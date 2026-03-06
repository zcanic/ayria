"""Environment event ingress.

This file is strategically important because `ayria` is not driven only by user
chat input. Window changes, screenshot captures, idle transitions, and other
signals enter the system here.

Implementation notes:
- Keep each route narrow and explicit.
- Convert transport payloads into domain events, then hand off to services.
- Duplicate watcher events are normal; services should tolerate them.
- Do not decide proactive behavior in the route layer.
"""

from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
import time

from app.domain.models.world_state import ActiveWindow, ScreenshotSummary
from app.runtime_container import container

router = APIRouter(prefix='/events', tags=['events'])


class WindowChangedRequest(BaseModel):
    app_name: str
    window_title: str
    url: str | None = None


class ScreenshotCapturedRequest(BaseModel):
    image_path: str
    captured_at: str


@router.post('/window-changed')
def window_changed(request: WindowChangedRequest) -> dict:
    updated = container.world_state_repo.update_active_window(
        ActiveWindow(
            app_name=request.app_name,
            window_title=request.window_title,
            url=request.url,
        )
    )
    return {'accepted': True, 'event': 'window.changed', 'payload': request.model_dump(), 'world_state': updated.model_dump()}


@router.post('/screenshot-captured')
def screenshot_captured(request: ScreenshotCapturedRequest) -> dict:
    active_window = container.world_state_repo.get().active_window
    active_app_name = active_window.app_name if active_window else None
    active_window_title = active_window.window_title if active_window else None
    allowed, reason = container.presence_service.is_screenshot_ingestion_allowed(
        screenshot_enabled=container.config.screenshot_enabled,
        active_app_name=active_app_name,
        active_window_title=active_window_title,
    )
    if not allowed:
        return {
            'accepted': True,
            'event': 'screenshot.captured',
            'payload': request.model_dump(),
            'policy_blocked': True,
            'policy_reason': reason,
            'analyzed': False,
            'stored': False,
        }

    analysis = asyncio.run(container.screenshot_analyzer.analyze(request.image_path))
    summary = ScreenshotSummary(
        image_id=request.image_path,
        summary=analysis['summary'],
        detected_entities=analysis['detected_entities'],
        scene_type=analysis['scene_type'],
        confidence=float(analysis['confidence']),
    )
    updated = container.world_state_repo.add_screenshot_summary(summary)

    proactive_considered = container.presence_service.should_consider_proactive_message(
        active_app_name=updated.active_window.app_name if updated.active_window else None,
        user_is_actively_typing=False,
        observation_confidence=summary.confidence,
        now_ts=time.time(),
    )
    proactive_message_emitted = False
    if proactive_message_emitted:
        container.presence_service.mark_proactive_emitted(now_ts=time.time())

    return {
        'accepted': True,
        'event': 'screenshot.captured',
        'payload': request.model_dump(),
        'screenshot_summary': summary.model_dump(),
        'policy_blocked': False,
        'policy_reason': 'allowed',
        'analyzed': True,
        'stored': True,
        'eligible_for_proactive': proactive_considered,
        'proactive_message_emitted': proactive_message_emitted,
        'world_state': updated.model_dump(),
    }
