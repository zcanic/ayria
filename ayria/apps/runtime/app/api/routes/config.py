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
    fallback_provider: str | None = None
    fallback_model: str | None = None
    proactive_enabled: bool | None = None
    proactive_mode: str | None = None
    proactive_cooldown_seconds: int | None = None
    screenshot_enabled: bool | None = None
    blacklisted_apps: list[str] | None = None
    screenshot_blocked_scene_types: list[str] | None = None
    provider_stub_mode: bool | None = None
    persona_intensity: str | None = None
    permission_safe_read_policy: str | None = None
    permission_external_read_policy: str | None = None
    permission_sensitive_read_policy: str | None = None
    permission_action_policy: str | None = None


@router.put('')
def update_config(request: UpdateConfigRequest) -> dict:
    patch = {key: value for key, value in request.model_dump().items() if value is not None}
    previous = container.config.model_dump()
    next_config = container.config.model_copy(update=patch)
    container.apply_config(next_config)
    updated = container.config.model_dump()
    diff = {
        key: {
            'previous': previous.get(key),
            'current': updated.get(key),
        }
        for key in updated
        if previous.get(key) != updated.get(key)
    }
    container.event_stream.publish(
        'config.updated',
        {
            'diff': diff,
            'config': updated,
        },
    )
    container.audit_repo.append(
        category='config',
        action='config.updated',
        decision='applied',
        summary=f'Updated {len(diff)} config field(s)',
        metadata={'diff': diff},
    )
    return {'updated': True, 'config': updated, 'diff': diff}
