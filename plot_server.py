"""
plot_server.py - A simple MCP server that draws 4 kinds of charts.

Tools exposed:
  1. line_chart     - trends over time / ordered x values
  2. bar_chart      - compare values across categories
  3. pie_chart      - share of a whole
  4. scatter_plot   - relationship between two numeric variables

Each tool saves a PNG into PLOT_OUTPUT_DIR (default: ./plots) and returns the file path.
Runs over stdio, so any MCP client (our Ollama client, Claude Desktop, etc.) can launch it.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: never opens a window, never writes to stdout
import matplotlib.pyplot as plt

logging.getLogger("matplotlib").setLevel(logging.WARNING)  # hide noisy info logs

# MCP Python SDK 2.x renamed FastMCP -> MCPServer. Support both.
try:
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.server.fastmcp.exceptions import ToolError

OUTPUT_DIR = Path(os.getenv("PLOT_OUTPUT_DIR", Path(__file__).parent / "plots")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

mcp = _Server("plotter")


# ---------------------------------------------------------------- helpers
def _save(fig, kind: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40] or kind
    path = OUTPUT_DIR / f"{kind}_{slug}_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return str(path)


def _check_lengths(a, b, name_a: str, name_b: str) -> None:
    if not a or not b:
        raise ToolError(f"{name_a} and {name_b} must not be empty")
    if len(a) != len(b):
        raise ToolError(f"{name_a} has {len(a)} items but {name_b} has {len(b)}; they must match")


# ---------------------------------------------------------------- tools
@mcp.tool()
def line_chart(
    x: list[str],
    y: list[float],
    title: str = "Line Chart",
    xlabel: str = "X",
    ylabel: str = "Y",
) -> str:
    """Draw a line chart, best for trends over time (e.g. monthly sales).

    Args:
        x: Labels for the x axis in order, e.g. ["Jan", "Feb", "Mar"] or ["2021", "2022"].
        y: Numeric values, one per x label.
        title: Chart title.
        xlabel: X-axis label.
        ylabel: Y-axis label.
    """
    _check_lengths(x, y, "x", "y")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([str(v) for v in x], y, marker="o", linewidth=2)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(alpha=0.3)
    return f"Line chart saved to: {_save(fig, 'line', title)}"


@mcp.tool()
def bar_chart(
    categories: list[str],
    values: list[float],
    title: str = "Bar Chart",
    xlabel: str = "Category",
    ylabel: str = "Value",
) -> str:
    """Draw a bar chart, best for comparing amounts across categories.

    Args:
        categories: Category names, e.g. ["Apples", "Bananas", "Cherries"].
        values: Numeric value for each category.
        title: Chart title.
        xlabel: X-axis label.
        ylabel: Y-axis label.
    """
    _check_lengths(categories, values, "categories", "values")
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([str(c) for c in categories], values, color="#4C72B0")
    ax.bar_label(bars, fmt="%g")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(axis="y", alpha=0.3)
    return f"Bar chart saved to: {_save(fig, 'bar', title)}"


@mcp.tool()
def pie_chart(
    labels: list[str],
    values: list[float],
    title: str = "Pie Chart",
) -> str:
    """Draw a pie chart, best for showing parts of a whole (percentages / shares).

    Args:
        labels: Name of each slice, e.g. ["Rent", "Food", "Travel"].
        values: Positive number for each slice (need not add up to 100).
        title: Chart title.
    """
    _check_lengths(labels, values, "labels", "values")
    if any(v < 0 for v in values):
        raise ToolError("pie chart values must be non-negative")
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(values, labels=[str(l) for l in labels], autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    ax.axis("equal")
    return f"Pie chart saved to: {_save(fig, 'pie', title)}"


@mcp.tool()
def scatter_plot(
    x: list[float],
    y: list[float],
    title: str = "Scatter Plot",
    xlabel: str = "X",
    ylabel: str = "Y",
) -> str:
    """Draw a scatter plot, best for showing the relationship between two numeric variables.

    Args:
        x: Numeric x values, e.g. hours studied [1, 2, 3].
        y: Numeric y values, same length as x, e.g. exam scores [50, 60, 75].
        title: Chart title.
        xlabel: X-axis label.
        ylabel: Y-axis label.
    """
    _check_lengths(x, y, "x", "y")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(x, y, s=60, alpha=0.8, color="#DD8452", edgecolors="black")
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(alpha=0.3)
    return f"Scatter plot saved to: {_save(fig, 'scatter', title)}"


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
