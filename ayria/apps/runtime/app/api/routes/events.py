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

from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
import asyncio
import time
from typing import Literal, cast
from app.domain.models.world_state import ActiveWindow, ScreenshotSummary
from app.runtime_container import container
from datetime import datetime, timezone

router = APIRouter(prefix='/events', tags=['events'])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_screenshot_path(image_path: str) -> tuple[bool, str, Path | None]:
    path = Path(image_path).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    if not path.exists() or not path.is_file():
        return False, 'missing_file', None
    if path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
        return False, 'unsupported_image_type', None
    return True, 'trusted_local_file', path


def _maybe_emit_proactive_message(*, world_state, trigger: str) -> dict[str, object] | None:
    decision = container.runtime_policy_service.decide_proactive_observation(
        world_state=world_state,
        observation_confidence=0.85,
        user_is_actively_typing=False,
        now_ts=time.time(),
    )
    if not decision.allowed or not decision.suggestion:
        return None

    task = container.task_service.create_task(
        task_type='proactive_observation',
        payload={'trigger': trigger, 'active_window': world_state.active_window.model_dump() if world_state.active_window else None},
        priority=2,
    )
    message = container.proactive_service.build_message(
        message_id=f'proactive_{task.id}',
        text=decision.suggestion,
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
        summary=decision.suggestion,
        metadata={'task_id': task.id, 'trigger': trigger, 'response_mode': decision.response_mode},
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
def window_changed(request: WindowChangedRequest) -> dict[str, object]:
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
def screenshot_captured(request: ScreenshotCapturedRequest) -> dict[str, object]:
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
            'provenance_valid': False,
            'provenance_reason': 'policy_blocked',
            'analyzed': False,
            'stored': False,
            'world_state': current_world_state,
        }

    provenance_valid, provenance_reason, validated_path = _validate_screenshot_path(request.image_path)
    if not provenance_valid or validated_path is None:
        current_world_state = container.world_state_repo.get().model_dump()
        container.event_stream.publish('world_state.patched', current_world_state)
        return {
            'accepted': True,
            'event': 'screenshot.captured',
            'payload': request.model_dump(),
            'policy_blocked': False,
            'policy_reason': 'allowed',
            'provenance_valid': False,
            'provenance_reason': provenance_reason,
            'analyzed': False,
            'stored': False,
            'world_state': current_world_state,
        }

    analysis = asyncio.run(container.screenshot_analyzer.analyze(str(validated_path)))
    analysis_summary = str(analysis.get('summary', '')).strip() or 'screenshot analyzed'
    raw_entities = analysis.get('detected_entities')
    detected_entities = [str(item) for item in raw_entities] if isinstance(raw_entities, list) else []
    scene_type_value = str(analysis.get('scene_type', 'unknown')).strip() or 'unknown'
    if scene_type_value not in {'code', 'browser', 'document', 'chat', 'image', 'desktop', 'unknown'}:
        scene_type_value = 'unknown'
    scene_type = cast(Literal['code', 'browser', 'document', 'chat', 'image', 'desktop', 'unknown'], scene_type_value)
    confidence_value = analysis.get('confidence', 0.0)
    confidence = float(confidence_value) if isinstance(confidence_value, (int, float, str)) else 0.0
    summary = ScreenshotSummary(
        image_id=str(validated_path),
        summary=analysis_summary,
        detected_entities=detected_entities,
        scene_type=scene_type,
        confidence=confidence,
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
        'analysis_fallback_reason': analysis.get('analysis_fallback_reason'),
        'policy_blocked': False,
        'policy_reason': 'allowed',
        'provenance_valid': True,
        'provenance_reason': provenance_reason,
        'analyzed': True,
        'stored': True,
        'eligible_for_proactive': proactive_considered,
        'proactive_message_emitted': proactive_message_emitted,
        'proactive': proactive,
        'world_state': updated.model_dump(),
    }
