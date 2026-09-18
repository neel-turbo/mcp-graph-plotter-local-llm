# MCP Plotter + Ollama

A simple MCP server that draws **4 chart types**, driven by a **local LLM running in Ollama**.

| Tool | Best for |
|------|----------|
| `line_chart` | trends over time |
| `bar_chart` | comparing categories |
| `pie_chart` | parts of a whole |
| `scatter_plot` | relationship between two numbers |

```
You ──► ollama_client.py ──► Ollama (local LLM)
              │                  │ decides to call a tool
              ▼                  ▼
        plot_server.py (MCP, stdio) ──► plots/*.png
```

## Setup

```bash
# 1. Install Ollama (https://ollama.com) and pull a model that supports tool calling
ollama pull qwen3.5:2b          # alternatives: llama3.1, llama3.2, qwen3 mistral-nemo

# 2. Python deps (Python 3.10+)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python test_server.py            # optional: checks the server without the LLM

python ollama_client.py          # interactive chat
python ollama_client.py "Make a pie chart of my budget: rent 12000, food 6000, travel 2000"
```

Example prompts:
- `Plot monthly sales as a line chart: Jan 120, Feb 150, Mar 90, Apr 200`
- `Bar chart comparing populations of Delhi, Mumbai and Bangalore`
- `Scatter plot of hours studied 1-6 vs scores 45, 55, 60, 70, 78, 90`

Charts are saved to `./plots/` and opened automatically.

## MCP server configuration

Both `ollama_client.py` and `test_server.py` read the `plotter` entry from the project's `mcp.json`:

```json
{
  "mcpServers": {
    "plotter": {
      "command": "python",
      "args": ["plot_server.py"]
    }
  }
}
```

Activate the virtual environment before running either script so `python` uses the installed dependencies. You can also set `command` to the absolute path of your virtual environment's Python executable.

The server starts with the directory containing `mcp.json` as its working directory, so relative paths in `args` resolve there. An optional `env` object in the `plotter` entry can set server environment variables, for example `"env": {"PLOT_OUTPUT_DIR": "./plots"}`. Client settings such as `AUTO_OPEN` remain shell environment variables. Edit this file to change how the MCP server is launched; the client continues to discover its tools automatically.

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` | `qwen3.5:2b` | Any Ollama model with tool support |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `PLOT_OUTPUT_DIR` | `./plots` | Where PNGs are written |
| `AUTO_OPEN` | `1` | Set to `0` to stop auto-opening charts |

## Using the server with other MCP clients

`plot_server.py` is a standard stdio MCP server, so other hosts can use it too. Add the following entry to the other client's MCP configuration, using that client's required filename and location. Absolute paths avoid relying on its working directory:
```json
{
  "mcpServers": {
    "plotter": {
      "command": "/full/path/to/.venv/bin/python",
      "args": ["/full/path/to/plot_server.py"]
    }
  }
}
```

## Adding any chart type

Add a function decorated with `@mcp.tool()` in `plot_server.py` with type hints and a docstring.
The client discovers tools automatically, so no changes are needed there.

## Troubleshooting

- **"model does not support tools"**: pick a tool-capable model (see above).
- **Model answers in text instead of plotting**: small models (≤3B) are less reliable; try a 7B+ model or name the chart type explicitly.
- **Connection refused**: make sure Ollama is running (`ollama serve`).
- Works with MCP Python SDK 1.x and 2.x (2.x renamed `FastMCP` to `MCPServer`; both are handled).