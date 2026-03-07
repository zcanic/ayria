"""Clipboard tool.

Clipboard access stays explicit and observable. This implementation attempts to
read clipboard text on macOS through `pbpaste` and otherwise fails truthfully.
"""

from __future__ import annotations

import shutil
import subprocess


async def read_clipboard() -> dict:
    pbpaste = shutil.which('pbpaste')
    if pbpaste is None:
        return {'text': None, 'available': False, 'reason': 'pbpaste_unavailable'}

    result = subprocess.run([pbpaste], capture_output=True, text=True, timeout=2, check=False)
    if result.returncode != 0:
        raise RuntimeError(f'tool_clipboard_read_failed:{result.stderr.strip()}')
    return {'text': result.stdout or None, 'available': True}
