"""Main orchestration service.

This service should coordinate the runtime pipeline in a predictable order:
1. ingest event or user request
2. build/refresh world state
3. choose route
4. execute capability step
5. optionally call tools
6. run persona rewrite
7. emit task and message events

Do not bury these steps in route handlers.

This should eventually become the most important coordination point in the
runtime. A weaker agent should read this file before editing routes, providers,
or persona code.

Recommended future methods:
- handle_user_message(...)
- handle_domain_event(...)
- run_task(...)
- emit_assistant_message(...)
- maybe_schedule_proactive_message(...)
"""

from datetime import datetime, timezone
import asyncio

from app.domain.models.message import ChatMessage, MessagePart
from app.domain.models.world_state import PresenceState
from app.domain.services.context_service import ContextService
from app.domain.services.model_execution_service import ModelExecutionService
from app.domain.services.persona_service import PersonaService
from app.domain.services.presence_service import PresenceService
from app.domain.services.routing_service import RoutingService
from app.domain.services.task_service import TaskService
from app.infra.repositories.message_repo import MessageRepository
from app.infra.repositories.world_state_repo import WorldStateRepository


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Orchestrator:
    def __init__(
        self,
        *,
        task_service: TaskService,
        context_service: ContextService,
        routing_service: RoutingService,
        persona_service: PersonaService,
        model_execution_service: ModelExecutionService,
        presence_service: PresenceService,
        message_repo: MessageRepository,
        world_state_repo: WorldStateRepository,
    ) -> None:
        self._task_service = task_service
        self._context_service = context_service
        self._routing_service = routing_service
        self._persona_service = persona_service
        self._model_execution_service = model_execution_service
        self._presence_service = presence_service
        self._message_repo = message_repo
        self._world_state_repo = world_state_repo

    def handle_user_message(self, text: str, image_paths: list[str] | None = None) -> dict:
        now = _now_iso()
        self._world_state_repo.set_presence(
            PresenceState(
                mode='chatting',
                user_active=True,
                last_user_input_at=now,
                proactive_allowed=False,
            )
        )

        task = self._task_service.create_task(
            task_type='chat_reply',
            payload={'text': text, 'image_paths': image_paths or []},
            priority=3,
        )
        self._task_service.update_task(task.id, status='running')

        world_state = self._context_service.build_world_state()
        route = self._routing_service.choose_for_chat(has_images=bool(image_paths), current_world_state=world_state)

        self._world_state_repo.append_recent_message(text)

        if self._model_execution_service.provider_stub_mode:
            updated = self._task_service.update_task(
                task.id,
                status='failed',
                output_payload={
                    'route': route.model_dump(),
                    'inference_mode': 'stub',
                    'provider_call_occurred': False,
                    'reason': 'provider_stub_mode_enabled',
                },
            )
            self._world_state_repo.set_presence(
                PresenceState(
                    mode='idle',
                    user_active=True,
                    last_user_input_at=now,
                    proactive_allowed=False,
                )
            )
            return {
                'status': 'degraded',
                'taskId': task.id,
                'task': updated.model_dump() if updated else task.model_dump(),
                'route': route.model_dump(),
                'inference_mode': 'stub',
                'provider_call_occurred': False,
                'scaffold_message': 'Provider-backed inference is disabled in v1 stub mode.',
            }

        capability_text = text
        if world_state.active_window and world_state.active_window.window_title:
            capability_text = f"{text}\n\nCurrent active window: {world_state.active_window.window_title}"

        try:
            provider_result = asyncio.run(
                self._model_execution_service.run_chat(
                    provider_name=route.provider,
                    model=route.model,
                    text=capability_text,
                )
            )
            raw_model_text = str(provider_result.get('message', '')).strip()
            if not raw_model_text:
                raise RuntimeError('provider_empty_output')
        except Exception as error:
            reason = str(error)
            provider_call_occurred = not (
                reason.startswith('provider_unavailable:') or reason.startswith('provider_not_implemented:')
            )
            updated = self._task_service.update_task(
                task.id,
                status='failed',
                output_payload={
                    'route': route.model_dump(),
                    'inference_mode': 'provider_error',
                    'provider_call_occurred': provider_call_occurred,
                    'reason': reason,
                },
            )
            self._world_state_repo.set_presence(
                PresenceState(
                    mode='idle',
                    user_active=True,
                    last_user_input_at=now,
                    proactive_allowed=False,
                )
            )
            return {
                'status': 'failed',
                'taskId': task.id,
                'task': updated.model_dump() if updated else task.model_dump(),
                'route': route.model_dump(),
                'inference_mode': 'provider_error',
                'provider_call_occurred': provider_call_occurred,
                'error': reason,
            }

        final_text = self._persona_service.rewrite(capability_text=raw_model_text, intensity='normal')

        assistant_message = ChatMessage(
            id=f"msg_{task.id}",
            role='assistant',
            source='ui',
            parts=[MessagePart(type='text', text=final_text)],
            created_at=_now_iso(),
        )
        self._message_repo.append(assistant_message)

        updated = self._task_service.update_task(
            task.id,
            status='completed',
            output_payload={
                'route': route.model_dump(),
                'assistant_message_id': assistant_message.id,
                'inference_mode': 'provider',
                'provider_call_occurred': True,
                'provider_result': {
                    'provider': provider_result.get('provider'),
                    'model': provider_result.get('model'),
                },
            },
        )

        self._world_state_repo.set_presence(
            PresenceState(
                mode='idle',
                user_active=True,
                last_user_input_at=now,
                proactive_allowed=False,
            )
        )

        return {
            'status': 'accepted',
            'taskId': task.id,
            'task': updated.model_dump() if updated else task.model_dump(),
            'assistant_message': assistant_message.model_dump(),
            'route': route.model_dump(),
            'inference_mode': 'provider',
            'provider_call_occurred': True,
        }
