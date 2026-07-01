"""mcp_server — the MCP interface to DreamWork (the primary v1 UI, driven by cowork/Claude).

Named `mcp_server` (not `mcp`) so it doesn't shadow the `mcp` Python SDK. Keep it thin: tools
parse inputs and call `core`/modules, so the real logic stays reusable by a web UI later.
"""
