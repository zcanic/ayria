"""Controlled tool execution service.

Tool execution should remain explicit, inspectable, and policy-aware. This
service is the narrow execution layer used by routes or future orchestrator
steps.
"""

from __future__ import annotations

from app.providers.tools.clipboard_tool import read_clipboard
from app.providers.tools.desktop_snapshot import get_desktop_snapshot
from app.providers.tools.file_reader import read_file
from app.providers.tools.registry import ToolRegistry
from app.providers.tools.web_search import web_search


class ToolService:
    def __init__(self, registry: ToolRegistry, *, world_state_repo=None) -> None:
        self._registry = registry
        self._world_state_repo = world_state_repo

    def list_tools(self) -> list[dict]:
        return [tool.model_dump() for tool in self._registry.list_tools()]

    def get_tool(self, tool_name: str):
        return self._registry.get_tool(tool_name)

    def summarize_result_for_event(self, *, tool_name: str, result: dict) -> dict:
        tool = self._registry.get_tool(tool_name)
        summary = {
            'tool_name': tool_name,
            'event_result_mode': getattr(tool, 'event_result_mode', 'metadata_only') if tool is not None else 'metadata_only',
        }
        if tool_name == 'read_file':
            content = str(result.get('content', ''))
            summary.update(
                {
                    'path': result.get('path'),
                    'content_length': len(content),
                }
            )
            return summary
        if tool_name == 'clipboard_read':
            text = result.get('text')
            summary.update(
                {
                    'available': bool(result.get('available')),
                    'text_length': len(text) if isinstance(text, str) else 0,
                    'reason': result.get('reason'),
                }
            )
            return summary
        if tool_name == 'web_search':
            results = result.get('results') if isinstance(result.get('results'), list) else []
            summary.update(
                {
                    'query': result.get('query'),
                    'result_count': len(results),
                }
            )
            return summary
        if tool_name == 'desktop_snapshot':
            summary.update(
                {
                    'has_active_window': result.get('active_window') is not None,
                    'has_recent_screenshot': result.get('recent_screenshot') is not None,
                }
            )
            return summary
        if tool_name == 'memory_lookup':
            items = result.get('items') if isinstance(result.get('items'), list) else []
            summary.update({'query': result.get('query'), 'item_count': len(items)})
            return summary
        summary.update({'keys': sorted(result.keys())})
        return summary

    async def execute(self, *, tool_name: str, input_payload: dict, confirmed: bool) -> dict:
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            raise RuntimeError(f'tool_not_found:{tool_name}')
        if tool.requires_confirmation and not confirmed:
            raise RuntimeError(f'tool_confirmation_required:{tool_name}')

        if tool_name == 'web_search':
            query = str(input_payload.get('query', '')).strip()
            if not query:
                raise RuntimeError('tool_invalid_input:web_search:query_required')
            return await web_search(query)

        if tool_name == 'read_file':
            path = str(input_payload.get('path', '')).strip()
            if not path:
                raise RuntimeError('tool_invalid_input:read_file:path_required')
            return await read_file(path)

        if tool_name == 'clipboard_read':
            return await read_clipboard()

        if tool_name == 'desktop_snapshot':
            world_state = self._world_state_repo.get().model_dump() if self._world_state_repo is not None else {}
            return await get_desktop_snapshot(
                {
                    **input_payload,
                    'active_window': world_state.get('active_window'),
                    'recent_screenshot': (world_state.get('recent_screenshots') or [None])[0],
                }
            )

        if tool_name == 'memory_lookup':
            query = str(input_payload.get('query', '')).strip()
            return {'query': query, 'items': []}

        raise RuntimeError(f'tool_not_implemented:{tool_name}')
