from pathlib import Path
import asyncio

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.providers.vision.screenshot_analyzer import ScreenshotAnalyzer
from app.realtime.event_stream import EventStream
from app.runtime_container import RuntimeContainer


@pytest.fixture
def runtime_env(monkeypatch: pytest.MonkeyPatch) -> dict:
    test_container = RuntimeContainer()

    import app.api.routes.chat as chat_route
    import app.api.routes.audit as audit_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.memory as memory_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.tools as tools_route
    import app.api.routes.world_state as world_state_route
    import app.api.routes.ws as ws_route

    monkeypatch.setattr(audit_route, 'container', test_container)
    monkeypatch.setattr(chat_route, 'container', test_container)
    monkeypatch.setattr(config_route, 'container', test_container)
    monkeypatch.setattr(events_route, 'container', test_container)
    monkeypatch.setattr(health_route, 'container', test_container)
    monkeypatch.setattr(memory_route, 'container', test_container)
    monkeypatch.setattr(providers_route, 'container', test_container)
    monkeypatch.setattr(tasks_route, 'container', test_container)
    monkeypatch.setattr(tools_route, 'container', test_container)
    monkeypatch.setattr(world_state_route, 'container', test_container)
    monkeypatch.setattr(ws_route, 'container', test_container)

    return {'client': TestClient(app), 'container': test_container}


def _apply_runtime_overrides(container: RuntimeContainer, *, config_updates: dict | None = None, provider_overrides: dict | None = None) -> None:
    if config_updates:
        container.apply_config(container.config.model_copy(update=config_updates))
    for provider_name, provider in (provider_overrides or {}).items():
        container.override_provider(provider_name, provider)


def _receive_until_type(websocket, expected_type: str, *, max_events: int = 6) -> tuple[dict, list[dict]]:
    received: list[dict] = []
    for _ in range(max_events):
        event = websocket.receive_json()
        received.append(event)
        if event['type'] == expected_type:
            return event, received
    raise AssertionError(f'expected_event_not_received:{expected_type}:received={[item.get("type") for item in received]}')


def _receive_until_types(websocket, expected_types: set[str], *, max_events: int = 8) -> list[dict]:
    received: list[dict] = []
    seen: set[str] = set()
    for _ in range(max_events):
        event = websocket.receive_json()
        received.append(event)
        event_type = str(event.get('type'))
        if event_type in expected_types:
            seen.add(event_type)
        if seen == expected_types:
            return received
    raise AssertionError(f'expected_events_not_received:{sorted(expected_types)}:received={[item.get("type") for item in received]}')


def test_websocket_receives_world_state_patch(runtime_env: dict) -> None:
    client = runtime_env['client']
    with client.websocket_connect('/api/v1/ws') as websocket:
        ready = websocket.receive_json()
        assert ready['type'] == 'connection.ready'
        assert ready['source'] == 'runtime'
        assert 'id' in ready
        client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'main.py', 'url': None})
        first = websocket.receive_json()
        second = websocket.receive_json()
        types = {first['type'], second['type']}
        assert 'presence.updated' in types
        assert 'world_state.patched' in types
        world_state_event = first if first['type'] == 'world_state.patched' else second
        assert world_state_event['payload']['active_window']['app_name'] == 'Cursor'
        assert world_state_event['payload']['active_window']['window_title'] == 'main.py'


def test_tools_inventory_and_confirmation_rule(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']

    inventory = client.get('/api/v1/tools').json()
    names = {item['name'] for item in inventory['items']}
    assert 'read_file' in names
    assert 'web_search' in names

    sample = tmp_path / 'note.txt'
    sample.write_text('hello from file')

    approval_required = client.post('/api/v1/tools/execute', json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}})
    assert approval_required.status_code == 200
    assert approval_required.json()['status'] == 'awaiting_approval'
    assert approval_required.json()['task']['status'] == 'awaiting_user'
    assert approval_required.json()['task']['input_payload']['tool_name'] == 'read_file'

    allowed = client.post(
        '/api/v1/tools/execute',
        json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}, 'confirmed': True},
    )
    assert allowed.status_code == 200
    assert allowed.json()['result']['content'] == 'hello from file'


def test_tool_result_event_is_sanitized(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']
    sample = tmp_path / 'secret.txt'
    sample.write_text('very secret content')

    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.post(
            '/api/v1/tools/execute',
            json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}, 'confirmed': True},
        )
        assert response.status_code == 200

        result_event, received = _receive_until_type(websocket, 'tool.result', max_events=8)
        assert any(event['type'] == 'tool.called' for event in received)
        assert result_event['payload']['tool_name'] == 'read_file'
        assert result_event['payload']['content_length'] == len('very secret content')
        assert 'content' not in result_event['payload']

    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['category'] == 'tool'
    assert audit_logs[0]['decision'] == 'allowed'


def test_sensitive_tool_requests_approval_and_emits_permission_event(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']
    sample = tmp_path / 'secret.txt'
    sample.write_text('very secret content')

    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.post('/api/v1/tools/execute', json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}})
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'awaiting_approval'
        received = _receive_until_types(websocket, {'permission.requested', 'task.updated'}, max_events=6)
        permission_event = next(event for event in received if event['type'] == 'permission.requested')
        assert permission_event['payload']['tool_name'] == 'read_file'

    task_id = body['task']['id']
    listed = client.get('/api/v1/tasks').json()['items']
    matching = next(item for item in listed if item['id'] == task_id)
    assert matching['status'] == 'awaiting_user'

    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['decision'] == 'approval_required'


def test_task_decision_approve_executes_tool_and_completes_task(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']
    sample = tmp_path / 'todo.txt'
    sample.write_text('ship it')

    approval = client.post('/api/v1/tools/execute', json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}})
    task_id = approval.json()['task']['id']

    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.post(f'/api/v1/tasks/{task_id}/decision', json={'approve': True})
        assert response.status_code == 200
        body = response.json()
        assert body['status'] == 'completed'
        assert body['result']['content'] == 'ship it'

        result_event, received = _receive_until_type(websocket, 'tool.result', max_events=8)
        assert any(event['type'] == 'tool.called' for event in received)
        assert any(event['type'] == 'task.updated' for event in received)
        assert result_event['payload']['tool_name'] == 'read_file'

    task = client.get(f'/api/v1/tasks/{task_id}').json()
    assert task['status'] == 'completed'
    assert task['output_payload']['decision'] == 'approved'
    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['decision'] == 'approved'


def test_task_decision_reject_cancels_task(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']
    sample = tmp_path / 'todo.txt'
    sample.write_text('ship it')

    approval = client.post('/api/v1/tools/execute', json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}})
    task_id = approval.json()['task']['id']

    response = client.post(f'/api/v1/tasks/{task_id}/decision', json={'approve': False})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'rejected'
    assert body['task']['status'] == 'cancelled'

    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['decision'] == 'rejected'


def test_window_changed_can_emit_proactive_message(runtime_env: dict) -> None:
    client = runtime_env['client']
    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'proactive_enabled': True, 'proactive_mode': 'active', 'proactive_cooldown_seconds': 1},
    )

    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'main.py', 'url': None})
        assert response.status_code == 200
        body = response.json()
        assert body['proactive'] is not None
        proactive_event, _ = _receive_until_type(websocket, 'assistant.proactive.suggested', max_events=6)
        assert proactive_event['payload']['source'] == 'proactive'

    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['category'] == 'proactive'


def test_config_update_publishes_config_updated_event(runtime_env: dict) -> None:
    client = runtime_env['client']
    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.put('/api/v1/config', json={'persona_intensity': 'low'})
        assert response.status_code == 200
        event, received = _receive_until_type(websocket, 'config.updated', max_events=6)
        assert any(item['type'] == 'config.updated' for item in received)
        assert event['payload']['diff']['persona_intensity']['current'] == 'low'

    audit_logs = client.get('/api/v1/audit/logs').json()['items']
    assert audit_logs[0]['category'] == 'config'
    assert audit_logs[0]['action'] == 'config.updated'


def test_event_stream_reports_dropped_gap() -> None:
    stream = EventStream(max_events=2)
    stream.publish('one', {}, source='runtime')
    stream.publish('two', {}, source='runtime')
    stream.publish('three', {}, source='runtime')
    assert stream.oldest_seq() == 2
    dropped = stream.make_transient_event('events.dropped', {'from_seq': 1, 'to_seq': 1, 'dropped_count': 1}, seq=1)
    assert dropped['type'] == 'events.dropped'
    assert dropped['source'] == 'runtime'


def test_screenshot_analyzer_returns_structured_non_stub_data(runtime_env: dict) -> None:
    analyzer = runtime_env['container'].screenshot_analyzer
    result = asyncio.run(analyzer.analyze('/tmp/cursor_code_view.png'))
    assert result['scene_type'] == 'code'
    assert result['confidence'] > 0.5
    assert 'stub screenshot summary' not in result['summary']


def test_screenshot_analyzer_uses_model_backed_path_when_available(runtime_env: dict, tmp_path: Path) -> None:
    class FakeVisionProvider:
        implemented = True
        provider_id = 'ollama'
        supports_images = True

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            assert len(messages[0].get('images') or []) == 1
            return {
                'provider': 'ollama',
                'model': model,
                'message': 'A browser window showing Ayria documentation and a left navigation sidebar.',
            }

        async def health_check(self, model: str | None = None) -> dict:
            return {
                'configured': True,
                'implemented': True,
                'reachable': True,
                'status': 'ok',
                'supports_images': True,
            }

    image_path = tmp_path / 'browser-shot.png'
    image_path.write_bytes(b'\x89PNG\r\n\x1a\nfakepngdata')

    container = runtime_env['container']
    _apply_runtime_overrides(
        container,
        config_updates={'provider_stub_mode': False},
        provider_overrides={'ollama': FakeVisionProvider()},
    )
    analyzer = ScreenshotAnalyzer(
        model_execution_service=container.model_execution_service,
        provider_name='ollama',
        model='qwen3.5:0.8b',
    )

    result = asyncio.run(analyzer.analyze(str(image_path)))
    assert result['analysis_mode'] == 'provider_vision'
    assert result['scene_type'] == 'browser'
    assert result['provider'] == 'ollama'


def test_presence_state_includes_reason_and_focus(runtime_env: dict) -> None:
    client = runtime_env['client']
    response = client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'main.py', 'url': None})
    assert response.status_code == 200
    presence = response.json()['world_state']['presence']
    assert presence['reason'] == 'window_context_updated'
    assert presence['focus_label'] == 'Cursor / main.py'
