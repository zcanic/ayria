"""In-process runtime harness for eval scenarios.

The harness uses FastAPI TestClient against a fresh RuntimeContainer so runs are
repeatable and independent from external boot scripts.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
import time

from fastapi.testclient import TestClient

from app.core.config import AppConfig
from app.domain.models.world_state import ActiveWindow
from app.main import app
from app.runtime_container import RuntimeContainer


def _bind_container(container: RuntimeContainer) -> None:
    import app.api.routes.chat as chat_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.memory as memory_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.world_state as world_state_route

    chat_route.container = container
    config_route.container = container
    events_route.container = container
    health_route.container = container
    memory_route.container = container
    providers_route.container = container
    tasks_route.container = container
    world_state_route.container = container


@contextmanager
def runtime_client(config_overrides: dict | None = None) -> Iterator[tuple[TestClient, RuntimeContainer]]:
    container = RuntimeContainer()
    if config_overrides:
        next_config = container.config.model_copy(update=config_overrides)
        container.apply_config(next_config)
    _bind_container(container)
    yield TestClient(app), container


def seed_world_state(container: RuntimeContainer, payload: dict) -> None:
    active_window = payload.get('active_window')
    if isinstance(active_window, dict):
        container.world_state_repo.update_active_window(
            ActiveWindow(
                app_name=str(active_window.get('app_name', 'unknown')),
                window_title=str(active_window.get('window_title', 'unknown')),
                url=active_window.get('url'),
            )
        )

    presence = payload.get('presence')
    if isinstance(presence, dict):
        container.world_state_repo.set_presence(
            container.presence_service.build_presence_state(
                mode=str(presence.get('mode', 'idle')),
                user_active=bool(presence.get('user_is_actively_typing', False)),
            )
        )


def delay_ms(delay: int) -> None:
    time.sleep(delay / 1000.0)
