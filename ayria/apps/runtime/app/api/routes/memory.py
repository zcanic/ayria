"""Memory endpoints.

Memory is user-facing product surface, not just backend storage.
Design these endpoints carefully because they will shape trust and privacy.
"""

from fastapi import APIRouter

from app.runtime_container import container

router = APIRouter(prefix='/memory', tags=['memory'])


@router.get('/items')
def list_memory_items() -> dict:
    return {'items': []}
