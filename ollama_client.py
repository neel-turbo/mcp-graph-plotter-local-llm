"""
ollama_client.py - Chat with a local Ollama model that can draw charts via the MCP plot server.

Flow:
  you -> Ollama LLM -> (tool call) -> this client -> MCP plot_server.py -> PNG file
                    <- (tool result: file path) <-

Usage:
  python ollama_client.py                       # interactive chat
  python ollama_client.py "pie chart of ..."    # one-shot
Env vars:
  OLLAMA_MODEL  (default: qwen3.5:2b)  - must be a model that supports tool calling
  OLLAMA_HOST   (default: http://localhost:11434)
"""

import asyncio
import json
import os
import platform
import subprocess
import sys

from mcp import ClientSession
from mcp.client.stdio import stdio_client
from ollama import AsyncClient

from mcp_config import load_mcp_server

MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_TOOL_ROUNDS = 5
AUTO_OPEN = os.getenv("AUTO_OPEN", "1") == "1"  # open the PNG after it is created

SYSTEM_PROMPT = """You are a data visualization assistant with plotting tools:
line_chart (trends over time), bar_chart (compare categories),
pie_chart (parts of a whole), scatter_plot (relationship between two numeric variables).

When the user wants a chart:
- Pick the single best tool (or the one the user named).
- Pass data as JSON arrays of equal length, numbers as numbers (no units or % signs).
- Give a short meaningful title and axis labels.
If the user gives no data, invent small realistic sample data and say so.
After the tool returns, tell the user the file path it was saved to. Keep replies short."""


def mcp_tools_to_ollama(tools) -> list[dict]:
    """Convert MCP tool definitions into Ollama's function-calling format."""
    converted = []
    for tool in tools:
        data = tool.model_dump(by_alias=True)  # works for MCP SDK 1.x and 2.x
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": data["name"],
                    "description": data.get("description") or "",
                    "parameters": data["inputSchema"],
                },
            }
        )
    return converted


def result_to_text(result) -> tuple[str, bool]:
    """Flatten an MCP CallToolResult into plain text + error flag."""
    parts = [getattr(c, "text", "") for c in result.content]
    is_error = bool(getattr(result, "is_error", None) or getattr(result, "isError", False))
    return "\n".join(p for p in parts if p), is_error


def open_file(path: str) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass  # opening is a convenience; the path is still printed


async def run_turn(llm: AsyncClient, session: ClientSession, tools: list[dict], messages: list) -> str:
    """Send the conversation to the LLM, execute any tool calls, repeat until it answers."""
    for _ in range(MAX_TOOL_ROUNDS):
        response = await llm.chat(model=MODEL, messages=messages, tools=tools)
        msg = response.message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            name = call.function.name
            args = dict(call.function.arguments or {})
            print(f"  [tool] {name}({json.dumps(args)})")
            try:
                result = await session.call_tool(name, args)
                text, is_error = result_to_text(result)
            except Exception as exc:  # unknown tool, transport error, ...
                text, is_error = f"Error calling {name}: {exc}", True

            print(f"  [{'error' if is_error else 'result'}] {text}")
            if not is_error and AUTO_OPEN and "saved to:" in text:
                open_file(text.split("saved to:", 1)[1].strip())

            messages.append({"role": "tool", "content": text, "tool_name": name})

    return "(Stopped: too many tool calls in one turn.)"


async def main() -> None:
    server = load_mcp_server()

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = (await session.list_tools()).tools
            tools = mcp_tools_to_ollama(mcp_tools)
            llm = AsyncClient(host=OLLAMA_HOST)
            messages: list = [{"role": "system", "content": SYSTEM_PROMPT}]

            print(f"Model: {MODEL} | Tools: {', '.join(t.name for t in mcp_tools)}")

            # One-shot mode
            if len(sys.argv) > 1:
                messages.append({"role": "user", "content": " ".join(sys.argv[1:])})
                print("Assistant:", await run_turn(llm, session, tools, messages))
                return

            # Interactive mode
            print("Ask for a chart (type 'exit' to quit).\n")
            while True:
                user = (await asyncio.to_thread(input, "You: ")).strip()
                if user.lower() in {"exit", "quit", "q"}:
                    break
                if not user:
                    continue
                messages.append({"role": "user", "content": user})
                try:
                    print("Assistant:", await run_turn(llm, session, tools, messages), "\n")
                except Exception as exc:
                    print(f"Error talking to Ollama at {OLLAMA_HOST}: {exc}\n"
                          f"Is Ollama running and is '{MODEL}' pulled? (ollama pull {MODEL})\n")
                    messages.pop()  # drop the failed user message


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
