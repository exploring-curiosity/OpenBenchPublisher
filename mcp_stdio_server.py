"""Local MCP stdio server for the OpenBench Publisher app.

Run this with `uv run mcp_stdio_server.py` and point an MCP-capable client
(ChatGPT MCP, Claude Desktop, Cursor, etc.) at this command.
"""

from mcp_agent.server.app_server import create_mcp_server_for_app

from apps.mcp_agent_main import app


def main() -> None:
    """Start the MCP server over stdio.

    This uses FastMCP.run("stdio"), which internally runs the async stdio server.
    """
    server = create_mcp_server_for_app(app)
    server.run("stdio")


if __name__ == "__main__":
    main()
    main()
