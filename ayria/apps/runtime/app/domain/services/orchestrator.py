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
import json
from typing import Mapping

from app.domain.models.message import ChatMessage, MessagePart
from app.domain.services.context_service import ContextService
from app.domain.services.model_execution_service import ModelExecutionService
from app.domain.services.persona_service import PersonaService
from app.domain.services.presence_service import PresenceService
from app.domain.services.routing_service import RoutingService
from app.domain.services.runtime_policy_service import RuntimePolicyService
from app.domain.services.task_service import TaskService
from app.infra.repositories.message_repo import MessageRepository
from app.infra.repositories.world_state_repo import WorldStateRepository
from app.realtime.event_stream import EventStream


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
        tool_service,
        permission_policy_service,
        presence_service: PresenceService,
        runtime_policy_service: RuntimePolicyService,
        message_repo: MessageRepository,
        world_state_repo: WorldStateRepository,
        event_stream: EventStream,
        persona_intensity: str = 'normal',
    ) -> None:
        self._task_service = task_service
        self._context_service = context_service
        self._routing_service = routing_service
        self._persona_service = persona_service
        self._model_execution_service = model_execution_service
        self._tool_service = tool_service
        self._permission_policy_service = permission_policy_service
        self._presence_service = presence_service
        self._runtime_policy_service = runtime_policy_service
        self._message_repo = message_repo
        self._world_state_repo = world_state_repo
        self._event_stream = event_stream
        self._persona_intensity = persona_intensity

    def _set_presence(self, *, mode: str, user_active: bool) -> None:
        world_state = self._world_state_repo.set_presence(
            self._presence_service.build_presence_state(mode=mode, user_active=user_active)
        )
        self._event_stream.publish('presence.updated', world_state.presence.model_dump() if world_state.presence else {})
        self._event_stream.publish('world_state.patched', world_state.model_dump())

    def _format_error_reason(self, error: Exception) -> str:
        text = str(error).strip()
        if text:
            return text
        return f'{type(error).__name__}:{repr(error)}'

    def _compose_capability_text(self, *, text: str, model_context: Mapping[str, object], sanitized_window: Mapping[str, object]) -> str:
        capability_text = text
        if sanitized_window['visible'] and sanitized_window['window_title']:
            capability_text = f"{text}\n\nCurrent active window: {sanitized_window['window_title']}"
        recent_screenshot_summaries = model_context.get('recent_screenshot_summaries')
        if isinstance(recent_screenshot_summaries, list) and recent_screenshot_summaries:
            latest_summary = recent_screenshot_summaries[0]
            if isinstance(latest_summary, dict):
                summary_text = str(latest_summary.get('summary', '')).strip()
                scene_type = str(latest_summary.get('scene_type', '')).strip()
                if summary_text:
                    capability_text = (
                        f"{capability_text}\n\n"
                        f"Recent screenshot summary ({scene_type or 'unknown'}): {summary_text}"
                    )
        return capability_text

    def _build_model_tool_definitions(self) -> list[dict[str, object]]:
        specs = self._tool_service.list_tools()
        definitions: list[dict[str, object]] = []
        for spec in specs:
            definitions.append(
                {
                    'type': 'function',
                    'function': {
                        'name': spec['name'],
                        'description': spec['description'],
                        'parameters': spec.get('input_schema') or {'type': 'object'},
                    },
                }
            )
        return definitions

    def _extract_model_tool_calls(self, provider_result: dict[str, object]) -> list[dict[str, object]]:
        raw_calls = provider_result.get('tools_used')
        if not isinstance(raw_calls, list):
            return []
        parsed: list[dict[str, object]] = []
        for entry in raw_calls:
            if not isinstance(entry, dict):
                continue
            function_block = entry.get('function') if isinstance(entry.get('function'), dict) else entry
            name = str(function_block.get('name', '')).strip() if isinstance(function_block, dict) else ''
            if not name:
                continue
            arguments = function_block.get('arguments', {}) if isinstance(function_block, dict) else {}
            if isinstance(arguments, str):
                try:
                    decoded = json.loads(arguments)
                    arguments = decoded if isinstance(decoded, dict) else {}
                except Exception:
                    arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            parsed.append({'name': name, 'arguments': arguments})
        return parsed

    def _build_chat_continuation_payload(
        self,
        *,
        chat_task_id: str,
        original_text: str,
        image_paths: list[str],
        route: dict[str, object],
        context_exposure: dict[str, object],
    ) -> dict[str, object]:
        return {
            'type': 'chat_tool_call',
            'chat_task_id': chat_task_id,
            'original_text': original_text,
            'image_paths': image_paths,
            'route': route,
            'context_exposure': context_exposure,
        }

    def _tool_result_for_model(self, *, tool_name: str, tool_result: dict[str, object]) -> dict[str, object]:
        raw_json = json.dumps(tool_result, ensure_ascii=True)
        if len(raw_json) <= 1500:
            return tool_result
        summary = self._tool_service.summarize_result_for_event(tool_name=tool_name, result=tool_result)
        return {
            'truncated': True,
            'reason': 'tool_result_too_large_for_followup_prompt',
            'summary': summary,
            'raw_length': len(raw_json),
        }

    def continue_chat_after_tool(
        self,
        *,
        continuation: dict[str, object],
        tool_name: str,
        tool_result: dict[str, object],
    ) -> dict[str, object]:
        chat_task_id = str(continuation.get('chat_task_id', '')).strip()
        if not chat_task_id:
            raise RuntimeError('chat_continuation_missing_task_id')
        chat_task = self._task_service.get_task(chat_task_id)
        if chat_task is None:
            raise RuntimeError(f'chat_continuation_task_not_found:{chat_task_id}')

        route_value = continuation.get('route')
        route_payload: dict[str, object] = route_value if isinstance(route_value, dict) else {}
        provider_name = str(route_payload.get('provider', 'ollama')).strip() or 'ollama'
        model_name = str(route_payload.get('model', '')).strip() or 'qwen3.5:0.8b'
        original_text = str(continuation.get('original_text', '')).strip()

        tool_result_for_model = self._tool_result_for_model(tool_name=tool_name, tool_result=tool_result)
        tool_result_json = json.dumps(tool_result_for_model, ensure_ascii=True)
        tool_augmented_text = (
            f"{original_text}\n\n"
            f"Tool execution result for {tool_name}:\n"
            f"{tool_result_json}\n\n"
            "Use the tool result to produce the final answer."
        )

        world_state = self._context_service.build_world_state()
        model_context = self._context_service.build_model_context()
        active_window_context = model_context.get('active_window') if isinstance(model_context.get('active_window'), dict) else None
        user_message_policy = self._runtime_policy_service.decide_user_message(
            active_app_name=active_window_context.get('app_name') if active_window_context else None,
            active_window_title=active_window_context.get('window_title') if active_window_context else None,
        )
        context_exposure = user_message_policy.context_exposure or {}
        sanitized_window = context_exposure.get('active_window') or {'visible': False, 'window_title': None, 'reason': 'missing_context'}
        capability_text = self._compose_capability_text(text=tool_augmented_text, model_context=model_context, sanitized_window=sanitized_window)

        try:
            provider_result = asyncio.run(
                self._model_execution_service.run_chat(
                    provider_name=provider_name,
                    model=model_name,
                    text=capability_text,
                    image_paths=None,
                    tools=None,
                )
            )
            raw_model_text = str(provider_result.get('message', '')).strip()
            if not raw_model_text:
                raise RuntimeError('provider_empty_output')
        except Exception as error:
            reason = self._format_error_reason(error)
            updated = self._task_service.update_task(
                chat_task.id,
                status='failed',
                output_payload={
                    'route': route_payload,
                    'response_mode': user_message_policy.response_mode,
                    'context_exposure': context_exposure,
                    'inference_mode': 'provider_error',
                    'provider_call_occurred': True,
                    'reason': reason,
                    'continued_from_tool': tool_name,
                },
            )
            if updated is not None:
                self._event_stream.publish('task.updated', updated.model_dump())
            self._set_presence(mode='idle', user_active=True)
            return {
                'status': 'failed',
                'task': updated.model_dump() if updated else chat_task.model_dump(),
                'response_mode': user_message_policy.response_mode,
                'error': reason,
            }

        final_text = self._persona_service.rewrite(capability_text=raw_model_text, intensity=self._persona_intensity)
        assistant_message = ChatMessage(
            id=f"msg_{chat_task.id}",
            role='assistant',
            source='ui',
            parts=[MessagePart(type='text', text=final_text)],
            created_at=_now_iso(),
        )
        self._message_repo.append(assistant_message)
        self._event_stream.publish('assistant.message.created', assistant_message.model_dump())
        updated = self._task_service.update_task(
            chat_task.id,
            status='completed',
            output_payload={
                'route': route_payload,
                'response_mode': user_message_policy.response_mode,
                'assistant_message_id': assistant_message.id,
                'context_exposure': context_exposure,
                'inference_mode': 'provider',
                'provider_call_occurred': True,
                'provider_result': {
                    'provider': provider_result.get('provider'),
                    'model': provider_result.get('model'),
                },
                'continued_from_tool': tool_name,
            },
        )
        if updated is not None:
            self._event_stream.publish('task.updated', updated.model_dump())
        self._set_presence(mode='idle', user_active=True)
        return {
            'status': 'completed',
            'task': updated.model_dump() if updated else chat_task.model_dump(),
            'assistant_message': assistant_message.model_dump(),
            'response_mode': user_message_policy.response_mode,
            'inference_mode': 'provider',
            'provider_call_occurred': True,
        }

    def handle_user_message(self, text: str, image_paths: list[str] | None = None) -> dict[str, object]:
        current_world_state = self._world_state_repo.get()
        self._world_state_repo.set_presence(
            self._presence_service.presence_for_user_message(
                active_window_title=current_world_state.active_window.window_title if current_world_state.active_window else None
            )
        )
        updated_presence = self._world_state_repo.get()
        self._event_stream.publish('presence.updated', updated_presence.presence.model_dump() if updated_presence.presence else {})
        self._event_stream.publish('world_state.patched', updated_presence.model_dump())

        task = self._task_service.create_task(
            task_type='chat_reply',
            payload={'text': text, 'image_paths': image_paths or []},
            priority=3,
        )
        self._task_service.update_task(task.id, status='running')

        user_message = ChatMessage(
            id=f"user_{task.id}",
            role='user',
            source='ui',
            parts=[MessagePart(type='text', text=text)] + [MessagePart(type='image', image_url=path) for path in (image_paths or [])],
            created_at=_now_iso(),
        )
        self._message_repo.append(user_message)

        world_state = self._context_service.build_world_state()
        model_context = self._context_service.build_model_context()
        route = self._routing_service.choose_for_chat(has_images=bool(image_paths), current_world_state=world_state)
        active_window_context = model_context.get('active_window') if isinstance(model_context.get('active_window'), dict) else None
        user_message_policy = self._runtime_policy_service.decide_user_message(
            active_app_name=active_window_context.get('app_name') if active_window_context else None,
            active_window_title=active_window_context.get('window_title') if active_window_context else None,
        )
        context_exposure = user_message_policy.context_exposure or {}
        sanitized_window = context_exposure.get('active_window') or {'visible': False, 'window_title': None, 'reason': 'missing_context'}

        if self._model_execution_service.provider_stub_mode:
            updated = self._task_service.update_task(
                task.id,
                status='failed',
                output_payload={
                    'route': route.model_dump(),
                    'response_mode': user_message_policy.response_mode,
                    'context_exposure': context_exposure,
                    'inference_mode': 'stub',
                    'provider_call_occurred': False,
                    'reason': 'provider_stub_mode_enabled',
                },
            )
            if updated is not None:
                self._event_stream.publish('task.updated', updated.model_dump())
            self._set_presence(mode='idle', user_active=True)
            return {
                'status': 'degraded',
                'execution_mode': 'synchronous',
                'taskId': task.id,
                'task': updated.model_dump() if updated else task.model_dump(),
                'route': route.model_dump(),
                'response_mode': user_message_policy.response_mode,
                'context_exposure': context_exposure,
                'inference_mode': 'stub',
                'provider_call_occurred': False,
                'scaffold_message': 'Provider-backed inference is disabled in v1 stub mode.',
            }

        capability_text = self._compose_capability_text(text=text, model_context=model_context, sanitized_window=sanitized_window)
        tools_for_model = self._build_model_tool_definitions() if route.use_tools else None

        try:
            provider_result = asyncio.run(
                self._model_execution_service.run_chat(
                    provider_name=route.provider,
                    model=route.model,
                    text=capability_text,
                    image_paths=image_paths or None,
                    tools=tools_for_model,
                )
            )
            model_tool_calls = self._extract_model_tool_calls(provider_result)
            if model_tool_calls:
                first_call = model_tool_calls[0]
                tool_name = str(first_call.get('name', '')).strip()
                raw_tool_input_payload = first_call.get('arguments')
                tool_input_payload = raw_tool_input_payload if isinstance(raw_tool_input_payload, dict) else {}
                tool = self._tool_service.get_tool(tool_name)
                if tool is None:
                    raise RuntimeError(f'model_requested_unknown_tool:{tool_name}')

                permission = self._permission_policy_service.evaluate(tool=tool, confirmed=False)
                if permission.decision == 'denied':
                    updated = self._task_service.update_task(
                        task.id,
                        status='failed',
                        output_payload={
                            'route': route.model_dump(),
                            'response_mode': 'ask_permission',
                            'context_exposure': context_exposure,
                            'inference_mode': 'provider',
                            'provider_call_occurred': True,
                            'reason': permission.reason,
                            'tool_call': {'tool_name': tool_name, 'input_payload': tool_input_payload},
                        },
                    )
                    if updated is not None:
                        self._event_stream.publish('task.updated', updated.model_dump())
                    self._set_presence(mode='idle', user_active=True)
                    return {
                        'status': 'failed',
                        'execution_mode': 'synchronous',
                        'taskId': task.id,
                        'task': updated.model_dump() if updated else task.model_dump(),
                        'route': route.model_dump(),
                        'response_mode': 'ask_permission',
                        'context_exposure': context_exposure,
                        'inference_mode': 'provider',
                        'provider_call_occurred': True,
                        'error': permission.reason,
                    }

                continuation = self._build_chat_continuation_payload(
                    chat_task_id=task.id,
                    original_text=text,
                    image_paths=image_paths or [],
                    route=route.model_dump(),
                    context_exposure=context_exposure,
                )

                if permission.requires_approval:
                    response_mode = self._runtime_policy_service.response_mode_for_tool_permission(approval_required=True)
                    approval_task = self._task_service.create_task(
                        task_type='tool_call',
                        payload={
                            'tool_name': tool_name,
                            'input_payload': tool_input_payload,
                            'permission': permission.model_dump(),
                            'continuation': continuation,
                            'parent_chat_task_id': task.id,
                        },
                        priority=4,
                    )
                    approval_task = self._task_service.update_task(
                        approval_task.id,
                        status='awaiting_user',
                        output_payload={'reason': permission.reason, 'tool_name': tool_name, 'response_mode': response_mode},
                    ) or approval_task
                    updated_chat_task = self._task_service.update_task(
                        task.id,
                        status='awaiting_user',
                        output_payload={
                            'route': route.model_dump(),
                            'response_mode': response_mode,
                            'context_exposure': context_exposure,
                            'inference_mode': 'provider',
                            'provider_call_occurred': True,
                            'tool_call': {'tool_name': tool_name, 'input_payload': tool_input_payload},
                            'pending_tool_task_id': approval_task.id,
                        },
                    )
                    self._event_stream.publish('task.updated', (updated_chat_task or task).model_dump())
                    self._event_stream.publish('task.updated', approval_task.model_dump())
                    self._event_stream.publish(
                        'permission.requested',
                        {
                            'task_id': approval_task.id,
                            'tool_name': tool_name,
                            'reason': permission.reason,
                            'response_mode': response_mode,
                        },
                    )
                    self._set_presence(mode='idle', user_active=True)
                    return {
                        'status': 'awaiting_approval',
                        'execution_mode': 'synchronous',
                        'taskId': task.id,
                        'task': (updated_chat_task or task).model_dump(),
                        'route': route.model_dump(),
                        'response_mode': response_mode,
                        'context_exposure': context_exposure,
                        'inference_mode': 'provider',
                        'provider_call_occurred': True,
                        'tool_call': {'tool_name': tool_name, 'input_payload': tool_input_payload},
                        'approval_task': approval_task.model_dump(),
                    }

                tool_task = self._task_service.create_task(
                    task_type='tool_call',
                    payload={
                        'tool_name': tool_name,
                        'input_payload': tool_input_payload,
                        'permission': permission.model_dump(),
                        'continuation': continuation,
                        'parent_chat_task_id': task.id,
                    },
                    priority=4,
                )
                running_tool_task = self._task_service.update_task(
                    tool_task.id,
                    status='running',
                    output_payload={'reason': permission.reason, 'tool_name': tool_name, 'response_mode': 'respond_now'},
                ) or tool_task
                self._event_stream.publish('task.updated', running_tool_task.model_dump())
                self._event_stream.publish(
                    'tool.called',
                    {
                        'tool_name': tool_name,
                        'confirmed': False,
                        'permission_level': getattr(tool, 'permission_level', None),
                        'data_sensitivity': getattr(tool, 'data_sensitivity', None),
                        'approved_via_task': running_tool_task.id,
                    },
                )
                try:
                    tool_result = asyncio.run(
                        self._tool_service.execute(
                            tool_name=tool_name,
                            input_payload=tool_input_payload,
                            confirmed=False,
                        )
                    )
                except Exception as tool_error:
                    reason = self._format_error_reason(tool_error)
                    failed_tool_task = self._task_service.update_task(
                        running_tool_task.id,
                        status='failed',
                        output_payload={'decision': 'allowed_but_failed', 'error': reason, 'tool_name': tool_name},
                    ) or running_tool_task
                    failed_chat_task = self._task_service.update_task(
                        task.id,
                        status='failed',
                        output_payload={
                            'route': route.model_dump(),
                            'response_mode': user_message_policy.response_mode,
                            'context_exposure': context_exposure,
                            'inference_mode': 'provider_error',
                            'provider_call_occurred': True,
                            'reason': f'tool_execution_failed:{tool_name}:{reason}',
                        },
                    ) or task
                    self._event_stream.publish('tool.failed', {'tool_name': tool_name, 'error': reason, 'approved_via_task': running_tool_task.id})
                    self._event_stream.publish('task.updated', failed_tool_task.model_dump())
                    self._event_stream.publish('task.updated', failed_chat_task.model_dump())
                    self._set_presence(mode='idle', user_active=True)
                    return {
                        'status': 'failed',
                        'execution_mode': 'synchronous',
                        'taskId': task.id,
                        'task': failed_chat_task.model_dump(),
                        'route': route.model_dump(),
                        'response_mode': user_message_policy.response_mode,
                        'context_exposure': context_exposure,
                        'inference_mode': 'provider_error',
                        'provider_call_occurred': True,
                        'error': f'tool_execution_failed:{tool_name}:{reason}',
                    }

                completed_tool_task = self._task_service.update_task(
                    running_tool_task.id,
                    status='completed',
                    output_payload={
                        'decision': 'allowed',
                        'tool_name': tool_name,
                        'response_mode': 'respond_now',
                        'result': self._tool_service.summarize_result_for_event(tool_name=tool_name, result=tool_result),
                    },
                ) or running_tool_task
                self._event_stream.publish(
                    'tool.result',
                    {
                        **self._tool_service.summarize_result_for_event(tool_name=tool_name, result=tool_result),
                        'approved_via_task': running_tool_task.id,
                    },
                )
                self._event_stream.publish('task.updated', completed_tool_task.model_dump())
                return self.continue_chat_after_tool(
                    continuation=continuation,
                    tool_name=str(tool_name),
                    tool_result=tool_result,
                )

            raw_model_text = str(provider_result.get('message', '')).strip()
            if not raw_model_text:
                raise RuntimeError('provider_empty_output')
        except Exception as error:
            reason = self._format_error_reason(error)
            provider_call_occurred = not (
                reason.startswith('provider_unavailable:') or reason.startswith('provider_not_implemented:')
            )
            updated = self._task_service.update_task(
                task.id,
                status='failed',
                output_payload={
                    'route': route.model_dump(),
                    'response_mode': user_message_policy.response_mode,
                    'context_exposure': context_exposure,
                    'inference_mode': 'provider_error',
                    'provider_call_occurred': provider_call_occurred,
                    'reason': reason,
                },
            )
            if updated is not None:
                self._event_stream.publish('task.updated', updated.model_dump())
            self._set_presence(mode='idle', user_active=True)
            return {
                'status': 'failed',
                'execution_mode': 'synchronous',
                'taskId': task.id,
                'task': updated.model_dump() if updated else task.model_dump(),
                'route': route.model_dump(),
                'response_mode': user_message_policy.response_mode,
                'context_exposure': context_exposure,
                'inference_mode': 'provider_error',
                'provider_call_occurred': provider_call_occurred,
                'error': reason,
            }

        final_text = self._persona_service.rewrite(capability_text=raw_model_text, intensity=self._persona_intensity)

        assistant_message = ChatMessage(
            id=f"msg_{task.id}",
            role='assistant',
            source='ui',
            parts=[MessagePart(type='text', text=final_text)],
            created_at=_now_iso(),
        )
        self._message_repo.append(assistant_message)
        self._event_stream.publish('assistant.message.created', assistant_message.model_dump())

        updated = self._task_service.update_task(
            task.id,
            status='completed',
            output_payload={
                'route': route.model_dump(),
                'response_mode': user_message_policy.response_mode,
                'assistant_message_id': assistant_message.id,
                'context_exposure': context_exposure,
                'inference_mode': 'provider',
                'provider_call_occurred': True,
                'provider_result': {
                    'provider': provider_result.get('provider'),
                    'model': provider_result.get('model'),
                },
                },
            )
        if updated is not None:
            self._event_stream.publish('task.updated', updated.model_dump())

        self._set_presence(mode='idle', user_active=True)

        return {
            'status': 'completed',
            'execution_mode': 'synchronous',
            'taskId': task.id,
            'task': updated.model_dump() if updated else task.model_dump(),
            'assistant_message': assistant_message.model_dump(),
            'route': route.model_dump(),
            'response_mode': user_message_policy.response_mode,
            'context_exposure': context_exposure,
            'inference_mode': 'provider',
            'provider_call_occurred': True,
        }
