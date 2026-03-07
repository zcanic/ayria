from pathlib import Path
import asyncio

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.domain.services.model_execution_service import ModelExecutionService
from app.providers.vision.screenshot_analyzer import ScreenshotAnalyzer
from app.realtime.event_stream import EventStream
from app.runtime_container import RuntimeContainer


@pytest.fixture
def runtime_env(monkeypatch: pytest.MonkeyPatch) -> dict:
    test_container = RuntimeContainer()

    import app.api.routes.chat as chat_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.memory as memory_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.tools as tools_route
    import app.api.routes.world_state as world_state_route
    import app.api.routes.ws as ws_route

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
        assert 'presence.updated' in types or 'world_state.patched' in types


def test_tools_inventory_and_confirmation_rule(runtime_env: dict, tmp_path: Path) -> None:
    client = runtime_env['client']

    inventory = client.get('/api/v1/tools').json()
    names = {item['name'] for item in inventory['items']}
    assert 'read_file' in names
    assert 'web_search' in names

    sample = tmp_path / 'note.txt'
    sample.write_text('hello from file')

    denied = client.post('/api/v1/tools/execute', json={'tool_name': 'read_file', 'input_payload': {'path': str(sample)}})
    assert denied.status_code == 400
    assert 'tool_confirmation_required:read_file' in denied.json()['detail']

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

        events = [websocket.receive_json(), websocket.receive_json()]
        result_event = next(event for event in events if event['type'] == 'tool.result')
        assert result_event['payload']['tool_name'] == 'read_file'
        assert result_event['payload']['content_length'] == len('very secret content')
        assert 'content' not in result_event['payload']


def test_config_update_publishes_config_updated_event(runtime_env: dict) -> None:
    client = runtime_env['client']
    with client.websocket_connect('/api/v1/ws') as websocket:
        websocket.receive_json()
        response = client.put('/api/v1/config', json={'persona_intensity': 'low'})
        assert response.status_code == 200
        event = websocket.receive_json()
        while event['type'] != 'config.updated':
            event = websocket.receive_json()
        assert event['payload']['diff']['persona_intensity']['current'] == 'low'


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
    container.config.provider_stub_mode = False
    container.llm_providers['ollama'] = FakeVisionProvider()
    container.model_execution_service = ModelExecutionService(provider_stub_mode=False, providers=container.llm_providers)
    analyzer = ScreenshotAnalyzer(
        model_execution_service=container.model_execution_service,
        provider_name='ollama',
        model='qwen3.5:0.8b',
    )

    result = asyncio.run(analyzer.analyze(str(image_path)))
    assert result['analysis_mode'] == 'provider_vision'
    assert result['scene_type'] == 'browser'
    assert result['provider'] == 'ollama'
