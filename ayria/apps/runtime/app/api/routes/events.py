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
from datetime import datetime, timezone

router = APIRouter(prefix='/events', tags=['events'])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _maybe_emit_proactive_message(*, world_state, trigger: str) -> dict | None:
    proactive_considered = container.presence_service.should_consider_proactive_message(
        active_app_name=world_state.active_window.app_name if world_state.active_window else None,
        user_is_actively_typing=False,
        observation_confidence=0.85,
        now_ts=time.time(),
    )
    if not proactive_considered:
        return None

    suggestion = container.proactive_service.suggest_for_world_state(world_state)
    if not suggestion:
        return None

    task = container.task_service.create_task(
        task_type='proactive_observation',
        payload={'trigger': trigger, 'active_window': world_state.active_window.model_dump() if world_state.active_window else None},
        priority=2,
    )
    message = container.proactive_service.build_message(
        message_id=f'proactive_{task.id}',
        text=suggestion,
        created_at=_now_iso(),
    )
    container.message_repo.append(message)
    updated_task = container.task_service.update_task(
        task.id,
        status='completed',
        output_payload={'assistant_message_id': message.id, 'trigger': trigger},
    ) or task
    container.presence_service.mark_proactive_emitted(now_ts=time.time())
    updated_presence = container.world_state_repo.set_presence(
        container.presence_service.build_presence_state(
            mode='idle',
            user_active=True,
            reason='proactive_message_emitted',
            focus_label=world_state.active_window.window_title if world_state.active_window else None,
        )
    )
    container.audit_repo.append(
        category='proactive',
        action='assistant.proactive.suggested',
        decision='emitted',
        summary=suggestion,
        metadata={'task_id': task.id, 'trigger': trigger},
    )
    container.event_stream.publish('assistant.proactive.suggested', message.model_dump())
    container.event_stream.publish('assistant.message.created', message.model_dump())
    container.event_stream.publish('task.updated', updated_task.model_dump())
    container.event_stream.publish('presence.updated', updated_presence.presence.model_dump() if updated_presence.presence else {})
    container.event_stream.publish('world_state.patched', updated_presence.model_dump())
    return {'task': updated_task.model_dump(), 'message': message.model_dump()}


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
    updated = container.world_state_repo.set_presence(
        container.presence_service.presence_for_window(
            active_app_name=request.app_name,
            active_window_title=request.window_title,
        )
    )
    container.event_stream.publish('presence.updated', updated.presence.model_dump() if updated.presence else {})
    container.event_stream.publish('world_state.patched', updated.model_dump())
    proactive = _maybe_emit_proactive_message(world_state=updated, trigger='window.changed')
    return {'accepted': True, 'event': 'window.changed', 'payload': request.model_dump(), 'world_state': updated.model_dump(), 'proactive': proactive}


@router.post('/screenshot-captured')
def screenshot_captured(request: ScreenshotCapturedRequest) -> dict:
    current_world_state = container.world_state_repo.get()
    current_window = current_world_state.active_window
    container.world_state_repo.set_presence(
        container.presence_service.presence_for_observation(
            active_app_name=current_window.app_name if current_window else None,
            active_window_title=current_window.window_title if current_window else None,
        )
    )

    active_window = container.world_state_repo.get().active_window
    active_app_name = active_window.app_name if active_window else None
    active_window_title = active_window.window_title if active_window else None
    allowed, reason = container.presence_service.is_screenshot_ingestion_allowed(
        screenshot_enabled=container.config.screenshot_enabled,
        active_app_name=active_app_name,
        active_window_title=active_window_title,
    )
    if not allowed:
        current_world_state = container.world_state_repo.get().model_dump()
        container.event_stream.publish('world_state.patched', current_world_state)
        return {
            'accepted': True,
            'event': 'screenshot.captured',
            'payload': request.model_dump(),
            'policy_blocked': True,
            'policy_reason': reason,
            'analyzed': False,
            'stored': False,
            'world_state': current_world_state,
        }

    analysis = asyncio.run(container.screenshot_analyzer.analyze(request.image_path))
    summary = ScreenshotSummary(
        image_id=request.image_path,
        summary=analysis['summary'],
        detected_entities=analysis['detected_entities'],
        scene_type=analysis['scene_type'],
        confidence=float(analysis['confidence']),
        analysis_mode=str(analysis.get('analysis_mode')) if analysis.get('analysis_mode') is not None else None,
        analysis_provider=str(analysis.get('provider')) if analysis.get('provider') is not None else None,
        analysis_model=str(analysis.get('model')) if analysis.get('model') is not None else None,
    )
    updated = container.world_state_repo.add_screenshot_summary(summary)
    container.event_stream.publish('world_state.patched', updated.model_dump())

    proactive = _maybe_emit_proactive_message(world_state=updated, trigger='screenshot.captured')
    proactive_considered = proactive is not None
    proactive_message_emitted = proactive is not None

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
        'proactive': proactive,
        'world_state': updated.model_dump(),
    }
