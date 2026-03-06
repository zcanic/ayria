"""Desktop snapshot tool placeholder.

This is a logical tool wrapper, not necessarily the OS-specific capture code.
OS capture may live in Tauri or a platform module; this tool simply normalizes
its usage inside the runtime.
"""

async def get_desktop_snapshot() -> dict:
    return {'image_path': None}
