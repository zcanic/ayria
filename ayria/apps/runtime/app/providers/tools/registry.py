"""Tool registry placeholder.

Register all tools here so the runtime can present a controlled tool inventory
to models and UI.
"""

from app.domain.models.tool import ToolSpec


class ToolRegistry:
    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name='web_search',
                description='Search public web sources',
                input_schema={'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
                requires_confirmation=True,
                timeout_seconds=20,
                permission_level='external_read',
                data_sensitivity='low',
                event_result_mode='metadata_only',
            ),
            ToolSpec(
                name='read_file',
                description='Read local file content',
                input_schema={'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']},
                requires_confirmation=True,
                timeout_seconds=10,
                permission_level='sensitive_read',
                data_sensitivity='high',
                event_result_mode='metadata_only',
            ),
            ToolSpec(
                name='desktop_snapshot',
                description='Capture desktop snapshot metadata',
                input_schema={'type': 'object', 'properties': {}},
                requires_confirmation=False,
                timeout_seconds=10,
                permission_level='safe_read',
                data_sensitivity='medium',
                event_result_mode='metadata_only',
            ),
            ToolSpec(
                name='clipboard_read',
                description='Read clipboard text',
                input_schema={'type': 'object', 'properties': {}},
                requires_confirmation=True,
                timeout_seconds=5,
                permission_level='sensitive_read',
                data_sensitivity='high',
                event_result_mode='metadata_only',
            ),
            ToolSpec(
                name='memory_lookup',
                description='Lookup relevant memory snippets',
                input_schema={'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
                requires_confirmation=False,
                timeout_seconds=5,
                permission_level='safe_read',
                data_sensitivity='medium',
                event_result_mode='metadata_only',
            ),
        ]

    def get_tool(self, tool_name: str) -> ToolSpec | None:
        for tool in self.list_tools():
            if tool.name == tool_name:
                return tool
        return None
