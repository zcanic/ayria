from fastapi.testclient import TestClient
import pytest
import asyncio
from pathlib import Path

from app.domain.models.world_state import ActiveWindow
from app.domain.services.presence_service import PresenceService
from app.main import app
from app.runtime_container import RuntimeContainer


@pytest.fixture
def runtime_env(monkeypatch: pytest.MonkeyPatch) -> dict:
    test_container = RuntimeContainer()

    import app.api.routes.chat as chat_route
    import app.api.routes.audit as audit_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.world_state as world_state_route

    monkeypatch.setattr(audit_route, 'container', test_container)
    monkeypatch.setattr(chat_route, 'container', test_container)
    monkeypatch.setattr(config_route, 'container', test_container)
    monkeypatch.setattr(events_route, 'container', test_container)
    monkeypatch.setattr(health_route, 'container', test_container)
    monkeypatch.setattr(providers_route, 'container', test_container)
    monkeypatch.setattr(tasks_route, 'container', test_container)
    monkeypatch.setattr(world_state_route, 'container', test_container)

    client = TestClient(app)
    client.headers.update({'X-Ayria-Token': test_container.config.runtime_api_token})
    return {'client': client, 'container': test_container}


@pytest.fixture
def runtime_client(runtime_env: dict) -> TestClient:
    return runtime_env['client']


def _apply_runtime_overrides(container: RuntimeContainer, *, config_updates: dict | None = None, provider_overrides: dict | None = None, removed_providers: list[str] | None = None) -> None:
    if config_updates:
        container.apply_config(container.config.model_copy(update=config_updates))
    for provider_name in removed_providers or []:
        container.remove_provider(provider_name)
    for provider_name, provider in (provider_overrides or {}).items():
        container.override_provider(provider_name, provider)


def test_health_endpoint(runtime_client: TestClient) -> None:
    response = runtime_client.get('/api/v1/health')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert body['service'] == 'ayria-runtime'


def test_chat_send_in_stub_mode_is_truthful(runtime_client: TestClient) -> None:
    response = runtime_client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'degraded'
    assert body['response_mode'] == 'respond_now'
    assert body['execution_mode'] == 'synchronous'
    assert body['inference_mode'] == 'stub'
    assert body['provider_call_occurred'] is False
    assert body['task']['status'] == 'failed'


def test_chat_send_live_mode_with_unreachable_provider_fails_truthfully(runtime_env: dict) -> None:
    class FakeUnreachableProvider:
        implemented = True
        provider_id = 'ollama'

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            raise AssertionError('chat should not run when provider health probe fails')

        async def health_check(self, model: str | None = None) -> dict:
            raise RuntimeError('All connection attempts failed')

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeUnreachableProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'failed'
    assert body['inference_mode'] == 'provider_error'
    assert body['provider_call_occurred'] is True
    assert 'All connection attempts failed' in body['error']


def test_chat_send_live_mode_with_missing_model_reports_install_guidance(runtime_env: dict) -> None:
    class FakeHealthOnlyProvider:
        implemented = True
        provider_id = 'ollama'

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            raise AssertionError('chat should not run when model is missing')

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'model_not_pulled'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeHealthOnlyProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'failed'
    assert body['provider_call_occurred'] is True
    assert 'model_not_pulled:ollama:qwen3.5:0.8b' in body['error']
    assert 'ollama pull qwen3.5:0.8b' in body['error']


def test_ollama_provider_normalizes_hf_style_model_aliases() -> None:
    from app.providers.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider()
    assert provider.normalize_model_name('Qwen3.5-0.8B') == 'qwen3.5:0.8b'
    assert provider.normalize_model_name('Qwen3.5-9B') == 'qwen3.5:9b'
    assert provider.normalize_model_name('custom-model') == 'custom-model'


def test_ollama_provider_disables_proxy_env_for_health_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.providers.llm import ollama_provider as ollama_module
    from app.providers.llm.ollama_provider import OllamaProvider

    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {'models': [{'name': 'qwen3.5:0.8b'}]}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(ollama_module.httpx, 'AsyncClient', FakeClient)

    provider = OllamaProvider()
    result = asyncio.run(provider.health_check(model='qwen3.5:0.8b'))
    assert captured['trust_env'] is False
    assert result['status'] == 'ok'


def test_chat_send_provider_unavailable_fails_truthfully(runtime_env: dict) -> None:
    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        removed_providers=['ollama'],
    )

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'failed'
    assert body['execution_mode'] == 'synchronous'
    assert body['provider_call_occurred'] is False
    assert 'provider_unavailable:ollama' in body['error']


def test_chat_send_provider_invalid_output_fails_truthfully(runtime_env: dict) -> None:
    class FakeBrokenProvider:
        implemented = True
        provider_id = 'ollama'

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'ollama', 'model': model, 'message': ''}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeBrokenProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'failed'
    assert body['execution_mode'] == 'synchronous'
    assert body['inference_mode'] == 'provider_error'
    assert body['provider_call_occurred'] is True
    assert 'provider_empty_output' in body['error']


def test_chat_send_live_mode_with_real_provider_path_is_completed(runtime_env: dict) -> None:
    class FakeWorkingProvider:
        implemented = True
        provider_id = 'ollama'

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'ollama', 'model': model, 'message': 'real reply'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeWorkingProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'completed'
    assert body['response_mode'] == 'respond_now'
    assert body['execution_mode'] == 'synchronous'
    assert body['provider_call_occurred'] is True
    assert body['assistant_message']['parts'][0]['text'] == 'real reply'


def test_chat_model_tool_call_requires_approval_and_decision_resumes_chat(runtime_env: dict, tmp_path: Path) -> None:
    sample = tmp_path / 'tool-note.txt'
    sample.write_text('tool content from disk')

    class FakeToolCallingProvider:
        implemented = True
        provider_id = 'ollama'
        calls = 0

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            FakeToolCallingProvider.calls += 1
            if FakeToolCallingProvider.calls == 1:
                assert isinstance(tools, list)
                assert any(item.get('function', {}).get('name') == 'read_file' for item in tools)
                return {
                    'provider': 'ollama',
                    'model': model,
                    'message': '',
                    'tools_used': [
                        {
                            'function': {
                                'name': 'read_file',
                                'arguments': {'path': str(sample)},
                            }
                        }
                    ],
                }

            assert 'Tool execution result for read_file' in messages[0]['content']
            assert 'tool content from disk' in messages[0]['content']
            return {'provider': 'ollama', 'model': model, 'message': 'final answer after approval'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeToolCallingProvider()},
    )

    send = client.post('/api/v1/chat/send', json={'text': 'read that file and summarize', 'image_paths': []})
    assert send.status_code == 200
    send_body = send.json()
    assert send_body['status'] == 'awaiting_approval'
    assert send_body['task']['status'] == 'awaiting_user'
    approval_task = send_body['approval_task']
    assert approval_task['status'] == 'awaiting_user'
    assert approval_task['input_payload']['tool_name'] == 'read_file'
    assert approval_task['input_payload']['parent_chat_task_id'] == send_body['task']['id']

    decision = client.post(f"/api/v1/tasks/{approval_task['id']}/decision", json={'approve': True})
    assert decision.status_code == 200
    decision_body = decision.json()
    assert decision_body['status'] == 'completed'
    assert decision_body['chat_response']['status'] == 'completed'
    assert decision_body['chat_response']['assistant_message']['parts'][0]['text'] == 'final answer after approval'

    chat_task = client.get(f"/api/v1/tasks/{send_body['task']['id']}").json()
    assert chat_task['status'] == 'completed'


def test_chat_continuation_truncates_large_tool_result_for_followup(runtime_env: dict, tmp_path: Path) -> None:
    sample = tmp_path / 'large-tool-note.txt'
    sample.write_text('X' * 5000)

    class FakeToolCallingProvider:
        implemented = True
        provider_id = 'ollama'
        calls = 0

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            FakeToolCallingProvider.calls += 1
            if FakeToolCallingProvider.calls == 1:
                return {
                    'provider': 'ollama',
                    'model': model,
                    'message': '',
                    'tools_used': [
                        {
                            'function': {
                                'name': 'read_file',
                                'arguments': {'path': str(sample)},
                            }
                        }
                    ],
                }

            content = messages[0]['content']
            assert 'tool_result_too_large_for_followup_prompt' in content
            assert '"truncated": true' in content.lower()
            return {'provider': 'ollama', 'model': model, 'message': 'ok after truncation'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeToolCallingProvider()},
    )

    send = client.post('/api/v1/chat/send', json={'text': 'read the file and answer', 'image_paths': []})
    assert send.status_code == 200
    send_body = send.json()
    assert send_body['status'] == 'awaiting_approval'

    approval_task_id = send_body['approval_task']['id']
    decision = client.post(f'/api/v1/tasks/{approval_task_id}/decision', json={'approve': True})
    assert decision.status_code == 200
    decision_body = decision.json()
    assert decision_body['status'] == 'completed'
    assert decision_body['chat_response']['status'] == 'completed'
    assert decision_body['chat_response']['assistant_message']['parts'][0]['text'] == 'ok after truncation'


def test_chat_model_tool_call_without_approval_executes_inline(runtime_env: dict) -> None:
    class FakeInlineToolProvider:
        implemented = True
        provider_id = 'ollama'
        calls = 0

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            FakeInlineToolProvider.calls += 1
            if FakeInlineToolProvider.calls == 1:
                assert isinstance(tools, list)
                assert any(item.get('function', {}).get('name') == 'memory_lookup' for item in tools)
                return {
                    'provider': 'ollama',
                    'model': model,
                    'message': '',
                    'tools_used': [
                        {
                            'function': {
                                'name': 'memory_lookup',
                                'arguments': {'query': 'roadmap'},
                            }
                        }
                    ],
                }

            assert 'Tool execution result for memory_lookup' in messages[0]['content']
            return {'provider': 'ollama', 'model': model, 'message': 'inline tool completed'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeInlineToolProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'check memory then answer', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'completed'
    assert body['assistant_message']['parts'][0]['text'] == 'inline tool completed'

    tasks = client.get('/api/v1/tasks').json()['items']
    tool_tasks = [item for item in tasks if item['type'] == 'tool_call']
    assert len(tool_tasks) >= 1
    assert tool_tasks[0]['status'] == 'completed'


def test_chat_send_live_mode_with_images_passes_multimodal_payload(runtime_env: dict, tmp_path) -> None:
    class FakeVisionProvider:
        implemented = True
        provider_id = 'ollama'
        supports_images = True

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            first = messages[0]
            assert first['role'] == 'user'
            assert isinstance(first.get('images'), list)
            assert len(first['images']) == 1
            assert isinstance(first['images'][0], str)
            return {'provider': 'ollama', 'model': model, 'message': 'saw-image'}

        async def health_check(self, model: str | None = None) -> dict:
            return {
                'configured': True,
                'implemented': True,
                'reachable': True,
                'status': 'ok',
                'supports_images': True,
            }

    image_path = tmp_path / 'sample.png'
    image_path.write_bytes(b'\x89PNG\r\n\x1a\nfakepngdata')

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False, 'vision_model': 'qwen3.5:0.8b'},
        provider_overrides={'ollama': FakeVisionProvider()},
    )

    response = client.post('/api/v1/chat/send', json={'text': 'what is in this image?', 'image_paths': [str(image_path)]})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'completed'
    assert body['assistant_message']['parts'][0]['text'] == 'saw-image'
    assert body['route']['model'] == 'qwen3.5:0.8b'


def test_window_changed_updates_world_state(runtime_client: TestClient) -> None:
    response = runtime_client.post(
        '/api/v1/events/window-changed',
        json={'app_name': 'Cursor', 'window_title': 'main.py', 'url': None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['world_state']['active_window']['app_name'] == 'Cursor'
    assert body['world_state']['active_window']['window_title'] == 'main.py'
    assert body['world_state']['presence']['mode'] == 'idle'


def test_presence_service_marks_blacklisted_context_as_protected() -> None:
    service = PresenceService(
        proactive_enabled=True,
        blacklisted_apps=['SecretsApp'],
        blocked_scene_types=['auth', 'payment', 'credential'],
    )
    protected, reason = service.is_context_protected(active_app_name='SecretsApp', active_window_title='vault')
    assert protected is True
    assert reason == 'blacklisted_app'

    sanitized = service.sanitize_active_window_for_model(active_app_name='SecretsApp', active_window_title='vault')
    assert sanitized['visible'] is False
    assert sanitized['window_title'] is None


def test_chat_context_redacts_protected_active_window(runtime_env: dict) -> None:
    class RecordingProvider:
        implemented = True
        provider_id = 'ollama'
        seen_text: str | None = None

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            RecordingProvider.seen_text = messages[0]['content']
            return {'provider': 'ollama', 'model': model, 'message': 'safe reply'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False, 'blacklisted_apps': ['SecretsApp']},
        provider_overrides={'ollama': RecordingProvider()},
    )

    client.post('/api/v1/events/window-changed', json={'app_name': 'SecretsApp', 'window_title': 'vault', 'url': None})
    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'completed'
    assert body['context_exposure']['active_window']['visible'] is False
    assert body['context_exposure']['active_window']['reason'] == 'blacklisted_app'
    assert RecordingProvider.seen_text is not None
    assert 'Current active window:' not in RecordingProvider.seen_text
    assert 'vault' not in RecordingProvider.seen_text


def test_chat_context_includes_recent_screenshot_summary(runtime_env: dict, tmp_path) -> None:
    class RecordingProvider:
        implemented = True
        provider_id = 'ollama'
        seen_text: str | None = None

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            RecordingProvider.seen_text = messages[0]['content']
            return {'provider': 'ollama', 'model': model, 'message': 'context-aware reply'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    image_path = tmp_path / 'browser-shot.png'
    image_path.write_bytes(b'\x89PNG\r\n\x1a\nfakepngdata')

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': RecordingProvider()},
    )

    client.post('/api/v1/events/window-changed', json={'app_name': 'Chrome', 'window_title': 'Ayria Docs', 'url': None})
    screenshot = client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': str(image_path), 'captured_at': '2026-03-08T00:00:00Z'},
    )
    assert screenshot.status_code == 200
    assert screenshot.json()['stored'] is True

    response = client.post('/api/v1/chat/send', json={'text': 'help me summarize this', 'image_paths': []})
    assert response.status_code == 200
    assert RecordingProvider.seen_text is not None
    assert 'Recent screenshot summary' in RecordingProvider.seen_text



def test_proactive_message_suppressed_for_protected_context(runtime_env: dict) -> None:
    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={
            'proactive_enabled': True,
            'proactive_mode': 'active',
            'blacklisted_apps': ['SecretsApp'],
            'proactive_cooldown_seconds': 1,
        },
    )

    response = client.post('/api/v1/events/window-changed', json={'app_name': 'SecretsApp', 'window_title': 'vault', 'url': None})
    assert response.status_code == 200
    body = response.json()
    assert body['proactive'] is None


def test_runtime_policy_service_allows_light_suggestion_for_visible_context(runtime_env: dict) -> None:
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'proactive_enabled': True, 'proactive_mode': 'active', 'proactive_cooldown_seconds': 1},
    )
    container.world_state_repo.update_active_window(
        ActiveWindow(app_name='Cursor', window_title='main.py', url=None)
    )
    decision = container.runtime_policy_service.decide_proactive_observation(
        world_state=container.context_service.build_world_state(),
        observation_confidence=0.9,
        user_is_actively_typing=False,
        now_ts=1000.0,
    )
    assert decision.allowed is True
    assert decision.response_mode == 'suggest_lightly'
    assert decision.reason == 'proactive_policy_allowed'
    assert decision.suggestion is not None


def test_runtime_policy_service_stays_silent_for_protected_context(runtime_env: dict) -> None:
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={
            'proactive_enabled': True,
            'proactive_mode': 'active',
            'proactive_cooldown_seconds': 1,
            'blacklisted_apps': ['SecretsApp'],
        },
    )
    container.world_state_repo.update_active_window(
        ActiveWindow(app_name='SecretsApp', window_title='vault', url=None)
    )
    decision = container.runtime_policy_service.decide_proactive_observation(
        world_state=container.context_service.build_world_state(),
        observation_confidence=0.9,
        user_is_actively_typing=False,
        now_ts=1000.0,
    )
    assert decision.allowed is False
    assert decision.response_mode == 'stay_silent'
    assert decision.reason == 'context_protected:blacklisted_app'


def test_screenshot_ingestion_allowed_path(runtime_client: TestClient, tmp_path) -> None:
    image_path = tmp_path / 'ok.png'
    image_path.write_bytes(b'\x89PNG\r\n\x1a\nfakepngdata')
    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': str(image_path), 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['policy_blocked'] is False
    assert body['provenance_valid'] is True
    assert body['analyzed'] is True
    assert body['stored'] is True
    assert body['world_state']['presence']['mode'] == 'observing'


def test_provider_inventory_reports_image_support(runtime_env: dict) -> None:
    client = runtime_env['client']
    providers = client.get('/api/v1/providers').json()
    ollama = next(item for item in providers['items'] if item['id'] == 'ollama')
    assert ollama['supports_images'] is True


def test_screenshot_ingestion_blocked_path(runtime_client: TestClient) -> None:
    runtime_client.put('/api/v1/config', json={'blacklisted_apps': ['SecretsApp']})
    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'SecretsApp', 'window_title': 'vault', 'url': None})
    response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': '/tmp/nope.png', 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['policy_blocked'] is True
    assert body['analyzed'] is False
    assert body['stored'] is False


def test_screenshot_ingestion_rejects_missing_file(runtime_client: TestClient) -> None:
    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': '/tmp/does-not-exist.png', 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['policy_blocked'] is False
    assert body['provenance_valid'] is False
    assert body['provenance_reason'] == 'missing_file'
    assert body['analyzed'] is False
    assert body['stored'] is False
    assert body['world_state']['recent_screenshots'] == []


def test_screenshot_ingestion_rejects_unsupported_file_type(runtime_client: TestClient, tmp_path) -> None:
    fake_file = tmp_path / 'not-image.txt'
    fake_file.write_text('not an image')
    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': str(fake_file), 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['policy_blocked'] is False
    assert body['provenance_valid'] is False
    assert body['provenance_reason'] == 'unsupported_image_type'
    assert body['analyzed'] is False
    assert body['stored'] is False


def test_presence_service_cooldown_consumed_only_on_emission() -> None:
    service = PresenceService(proactive_enabled=True, cooldown_seconds=60, blacklisted_apps=[])
    eligible = service.should_consider_proactive_message(
        active_app_name='Cursor',
        user_is_actively_typing=False,
        observation_confidence=0.9,
        now_ts=1000.0,
    )
    assert eligible is True

    eligible_without_emission = service.should_consider_proactive_message(
        active_app_name='Cursor',
        user_is_actively_typing=False,
        observation_confidence=0.9,
        now_ts=1010.0,
    )
    assert eligible_without_emission is True

    service.mark_proactive_emitted(now_ts=1010.0)
    blocked_after_emission = service.should_consider_proactive_message(
        active_app_name='Cursor',
        user_is_actively_typing=False,
        observation_confidence=0.9,
        now_ts=1020.0,
    )
    assert blocked_after_emission is False


def test_config_update_changes_runtime_behavior(runtime_client: TestClient) -> None:
    config_response = runtime_client.put(
        '/api/v1/config',
        json={
            'screenshot_enabled': False,
            'provider_stub_mode': True,
            'proactive_enabled': True,
            'proactive_cooldown_seconds': 42,
            'blacklisted_apps': ['BankApp'],
        },
    )
    assert config_response.status_code == 200
    config_body = config_response.json()['config']
    diff = config_response.json()['diff']
    assert config_body['screenshot_enabled'] is False
    assert config_body['proactive_cooldown_seconds'] == 42
    assert config_body['blacklisted_apps'] == ['BankApp']
    assert diff['screenshot_enabled']['current'] is False

    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    screenshot_response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': '/tmp/blocked.png', 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert screenshot_response.status_code == 200
    screenshot_body = screenshot_response.json()
    assert screenshot_body['policy_blocked'] is True
    assert screenshot_body['policy_reason'] == 'screenshot_disabled'


def test_providers_endpoint_reports_stub_and_health_semantics(runtime_client: TestClient) -> None:
    providers = runtime_client.get('/api/v1/providers').json()
    assert providers['runtime_mode'] == 'stub'
    ollama = next(item for item in providers['items'] if item['id'] == 'ollama')
    mlx = next(item for item in providers['items'] if item['id'] == 'mlx')
    assert ollama['configured'] is True
    assert ollama['implemented'] is True
    assert ollama['active_in_runtime_mode'] is False
    assert ollama['status'] == 'stub_mode'
    assert mlx['configured'] is False

    health = runtime_client.get('/api/v1/health/providers').json()
    assert health['runtime_mode'] == 'stub'
    ollama_health = next(item for item in health['providers'] if item['id'] == 'ollama')
    assert ollama_health['status'] == 'stub_mode'


def test_providers_endpoint_reports_live_mode_with_reachable_provider(runtime_env: dict) -> None:
    class FakeHealthyProvider:
        implemented = True
        provider_id = 'ollama'

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'ollama', 'model': model, 'message': 'unused'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeHealthyProvider()},
    )

    providers = client.get('/api/v1/providers').json()
    assert providers['runtime_mode'] == 'live'
    ollama = next(item for item in providers['items'] if item['id'] == 'ollama')
    assert ollama['configured'] is True
    assert ollama['implemented'] is True
    assert ollama['active_in_runtime_mode'] is True
    assert ollama['status'] == 'ok'

    health = client.get('/api/v1/health/providers').json()
    ollama_health = next(item for item in health['providers'] if item['id'] == 'ollama')
    assert ollama_health['status'] == 'ok'


def test_default_provider_config_changes_route_provider(runtime_env: dict) -> None:
    class FakeCloudProvider:
        implemented = True
        provider_id = 'cloud'
        supports_images = False

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'cloud', 'model': model, 'message': 'cloud reply'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    client = runtime_env['client']
    container = runtime_env['container']
    next_config = container.config.model_copy(
        update={
            'provider_stub_mode': False,
            'default_provider': 'cloud',
            'capability_model': 'cloud-model',
        }
    )
    container.override_provider('cloud', FakeCloudProvider())
    container.apply_config(next_config)

    response = client.post('/api/v1/chat/send', json={'text': 'hello', 'image_paths': []})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'completed'
    assert body['route']['provider'] == 'cloud'
    assert body['task']['output_payload']['provider_result']['provider'] == 'cloud'
