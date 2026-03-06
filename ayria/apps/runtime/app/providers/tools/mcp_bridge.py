"""MCP bridge placeholder.

This module should adapt MCP servers into the runtime's internal tool system.
Important for future integrations like filesystem, browser automation, grep_app,
and context-aware documentation servers.

Implementation note:
- keep MCP-specific protocol handling here
- expose a runtime-friendly tool inventory upward
- do not leak MCP transport details into persona or orchestrator code
"""

class MCPBridge:
    async def list_available_tools(self) -> list[dict]:
        return [
            {
                'name': 'mcp.filesystem.read_file',
                'description': 'Read file through MCP filesystem server',
                'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']},
            },
            {
                'name': 'mcp.context.docs_lookup',
                'description': 'Lookup official docs through MCP context server',
                'input_schema': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
            },
        ]
