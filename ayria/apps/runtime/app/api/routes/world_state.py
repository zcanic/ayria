from fastapi import APIRouter

from app.runtime_container import container


router = APIRouter(tags=['world-state'])


@router.get('/world-state')
def get_world_state() -> dict:
    return container.world_state_repo.get().model_dump()
