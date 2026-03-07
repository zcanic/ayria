from pathlib import Path
import asyncio

from fastapi.testclient import TestClient
import pytest

from app.main import app
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


def test_screenshot_analyzer_returns_structured_non_stub_data(runtime_env: dict) -> None:
    analyzer = runtime_env['container'].screenshot_analyzer
    result = asyncio.run(analyzer.analyze('/tmp/cursor_code_view.png'))
    assert result['scene_type'] == 'code'
    assert result['confidence'] > 0.5
    assert 'stub screenshot summary' not in result['summary']
