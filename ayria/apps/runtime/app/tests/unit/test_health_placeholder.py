from fastapi.testclient import TestClient
import pytest

from app.domain.services.presence_service import PresenceService
from app.main import app
from app.runtime_container import RuntimeContainer


@pytest.fixture
def runtime_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    test_container = RuntimeContainer()

    import app.api.routes.chat as chat_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.world_state as world_state_route

    monkeypatch.setattr(chat_route, 'container', test_container)
    monkeypatch.setattr(config_route, 'container', test_container)
    monkeypatch.setattr(events_route, 'container', test_container)
    monkeypatch.setattr(health_route, 'container', test_container)
    monkeypatch.setattr(providers_route, 'container', test_container)
    monkeypatch.setattr(tasks_route, 'container', test_container)
    monkeypatch.setattr(world_state_route, 'container', test_container)

    return TestClient(app)


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
    assert body['inference_mode'] == 'stub'
    assert body['provider_call_occurred'] is False
    assert body['task']['status'] == 'failed'


def test_window_changed_updates_world_state(runtime_client: TestClient) -> None:
    response = runtime_client.post(
        '/api/v1/events/window-changed',
        json={'app_name': 'Cursor', 'window_title': 'main.py', 'url': None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['world_state']['active_window']['app_name'] == 'Cursor'
    assert body['world_state']['active_window']['window_title'] == 'main.py'


def test_screenshot_ingestion_allowed_path(runtime_client: TestClient) -> None:
    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': '/tmp/ok.png', 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['policy_blocked'] is False
    assert body['analyzed'] is True
    assert body['stored'] is True


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
    assert config_body['screenshot_enabled'] is False
    assert config_body['proactive_cooldown_seconds'] == 42
    assert config_body['blacklisted_apps'] == ['BankApp']

    runtime_client.post('/api/v1/events/window-changed', json={'app_name': 'Cursor', 'window_title': 'editor', 'url': None})
    screenshot_response = runtime_client.post(
        '/api/v1/events/screenshot-captured',
        json={'image_path': '/tmp/blocked.png', 'captured_at': '2026-03-07T00:00:00Z'},
    )
    assert screenshot_response.status_code == 200
    screenshot_body = screenshot_response.json()
    assert screenshot_body['policy_blocked'] is True
    assert screenshot_body['policy_reason'] == 'screenshot_disabled'
