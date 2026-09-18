"""test_server.py - Check the MCP plot server works, without needing Ollama."""

import asyncio

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from mcp_config import load_mcp_server

SAMPLES = {
    "line_chart": {"x": ["Jan", "Feb", "Mar", "Apr"], "y": [10, 14, 9, 20], "title": "Monthly Sales"},
    "bar_chart": {"categories": ["Python", "JS", "Go"], "values": [45, 30, 25], "title": "Language Use"},
    "pie_chart": {"labels": ["Rent", "Food", "Travel"], "values": [50, 30, 20], "title": "Budget"},
    "scatter_plot": {"x": [1, 2, 3, 4, 5], "y": [52, 58, 65, 71, 80], "title": "Study vs Score"},
}


async def main() -> None:
    server = load_mcp_server()
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print("Tools:", [t.name for t in tools])
            for name, args in SAMPLES.items():
                result = await session.call_tool(name, args)
                print(" ", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
