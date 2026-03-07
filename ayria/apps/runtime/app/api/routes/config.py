"""Configuration endpoints.

Configuration must remain explicit and auditable.
Do not silently change privacy-sensitive settings based on model behavior.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.runtime_container import container

router = APIRouter(prefix='/config', tags=['config'])


@router.get('')
def get_config() -> dict:
    return container.config.model_dump()


class UpdateConfigRequest(BaseModel):
    default_provider: str | None = None
    capability_model: str | None = None
    vision_provider: str | None = None
    vision_model: str | None = None
    screenshot_analysis_provider: str | None = None
    screenshot_analysis_model: str | None = None
    proactive_enabled: bool | None = None
    proactive_cooldown_seconds: int | None = None
    screenshot_enabled: bool | None = None
    blacklisted_apps: list[str] | None = None
    screenshot_blocked_scene_types: list[str] | None = None
    provider_stub_mode: bool | None = None
    persona_intensity: str | None = None


@router.put('')
def update_config(request: UpdateConfigRequest) -> dict:
    patch = {key: value for key, value in request.model_dump().items() if value is not None}
    next_config = container.config.model_copy(update=patch)
    container.apply_config(next_config)
    return {'updated': True, 'config': container.config.model_dump()}
