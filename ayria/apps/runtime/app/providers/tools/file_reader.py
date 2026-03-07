"""File reader tool.

This is intentionally conservative:
- text files only
- small size limit
- explicit path echo in the result
"""

from __future__ import annotations

from pathlib import Path


async def read_file(path: str) -> dict:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise RuntimeError(f'tool_file_not_found:{target}')
    if not target.is_file():
        raise RuntimeError(f'tool_not_a_file:{target}')
    if target.stat().st_size > 64 * 1024:
        raise RuntimeError(f'tool_file_too_large:{target}')
    content = target.read_text(encoding='utf-8', errors='replace')
    return {'path': str(target), 'content': content}
