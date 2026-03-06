from app.domain.models.world_state import ActiveWindow, PresenceState, ScreenshotSummary, WorldState


class WorldStateRepository:
    def __init__(self) -> None:
        self._state = WorldState()

    def get(self) -> WorldState:
        return self._state.model_copy(deep=True)

    def save(self, state: WorldState) -> WorldState:
        self._state = state.model_copy(deep=True)
        return self.get()

    def update_active_window(self, window: ActiveWindow) -> WorldState:
        self._state.active_window = window
        return self.get()

    def set_presence(self, presence: PresenceState) -> WorldState:
        self._state.presence = presence
        return self.get()

    def add_screenshot_summary(self, summary: ScreenshotSummary, max_items: int = 5) -> WorldState:
        self._state.recent_screenshots.insert(0, summary)
        self._state.recent_screenshots = self._state.recent_screenshots[:max_items]
        return self.get()

    def append_recent_message(self, message: str, max_items: int = 10) -> WorldState:
        self._state.recent_messages.append(message)
        self._state.recent_messages = self._state.recent_messages[-max_items:]
        return self.get()

    def set_current_task_hint(self, task_hint: str | None) -> WorldState:
        self._state.current_task_hint = task_hint
        return self.get()
