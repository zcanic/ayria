"""Desktop snapshot tool.

This returns normalized snapshot metadata from the current known world state.
Real OS capture may still live elsewhere, but the runtime now has a truthful
tool surface for snapshot metadata.
"""

from __future__ import annotations


async def get_desktop_snapshot(context: dict | None = None) -> dict:
    context = context or {}
    active_window = context.get('active_window')
    recent_screenshot = context.get('recent_screenshot')
    return {
        'active_window': active_window,
        'recent_screenshot': recent_screenshot,
    }
