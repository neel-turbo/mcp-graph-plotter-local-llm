"""Load the plotter's stdio MCP server configuration from mcp.json."""

import json
from pathlib import Path

from mcp import StdioServerParameters

MCP_CONFIG = Path(__file__).resolve().with_name("mcp.json")


def load_mcp_server(config_path: Path = MCP_CONFIG) -> StdioServerParameters:
    """Read the plotter entry and resolve relative server paths beside the config."""
    config_path = config_path.resolve()
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read MCP configuration at {config_path}: {exc}") from exc

    try:
        entry = config["mcpServers"]["plotter"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"{config_path} must contain mcpServers.plotter") from exc

    if not isinstance(entry, dict):
        raise ValueError(f"mcpServers.plotter in {config_path} must be an object")
    if not isinstance(entry.get("command"), str) or not entry["command"].strip():
        raise ValueError(f"mcpServers.plotter.command in {config_path} must be a non-empty string")

    try:
        return StdioServerParameters(
            command=entry["command"],
            args=entry.get("args", []),
            env=entry.get("env"),
            cwd=str(config_path.parent),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid mcpServers.plotter configuration in {config_path}: {exc}") from exc
