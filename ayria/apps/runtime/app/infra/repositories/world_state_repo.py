from app.domain.models.world_state import ActiveWindow, PresenceState, ScreenshotSummary, WorldState
from threading import Lock


class WorldStateRepository:
    def __init__(self) -> None:
        self._state = WorldState()
        self._lock = Lock()

    def get(self) -> WorldState:
        with self._lock:
            return self._state.model_copy(deep=True)

    def save(self, state: WorldState) -> WorldState:
        with self._lock:
            self._state = state.model_copy(deep=True)
            return self._state.model_copy(deep=True)

    def update_active_window(self, window: ActiveWindow) -> WorldState:
        with self._lock:
            self._state.active_window = window
            return self._state.model_copy(deep=True)

    def set_presence(self, presence: PresenceState) -> WorldState:
        with self._lock:
            self._state.presence = presence
            return self._state.model_copy(deep=True)

    def add_screenshot_summary(self, summary: ScreenshotSummary, max_items: int = 5) -> WorldState:
        with self._lock:
            self._state.recent_screenshots.insert(0, summary)
            self._state.recent_screenshots = self._state.recent_screenshots[:max_items]
            return self._state.model_copy(deep=True)

    def append_recent_message(self, message: str, max_items: int = 10) -> WorldState:
        with self._lock:
            self._state.recent_messages.append(message)
            self._state.recent_messages = self._state.recent_messages[-max_items:]
            return self._state.model_copy(deep=True)

    def set_current_task_hint(self, task_hint: str | None) -> WorldState:
        with self._lock:
            self._state.current_task_hint = task_hint
            return self._state.model_copy(deep=True)
