"""Presence service.

This service decides whether the assistant should feel present without becoming
annoying. That means throttling, cooldowns, app blacklists, and user activity
awareness belong here.

This service is where product quality and annoyance risk meet.
If a future agent starts scattering cooldown checks in UI code, route files, or
prompt text, bring those rules back here.
"""

class PresenceService:
    def __init__(
        self,
        proactive_enabled: bool = False,
        cooldown_seconds: int = 300,
        blacklisted_apps: list[str] | None = None,
        blocked_scene_types: list[str] | None = None,
    ) -> None:
        self._proactive_enabled = proactive_enabled
        self._cooldown_seconds = cooldown_seconds
        self._blacklisted_apps = set(blacklisted_apps or [])
        self._blocked_scene_types = {item.lower() for item in (blocked_scene_types or [])}
        self._last_proactive_ts = 0.0

    def classify_scene_type(self, *, active_app_name: str | None, active_window_title: str | None) -> str:
        text = f"{active_app_name or ''} {active_window_title or ''}".lower()
        if any(keyword in text for keyword in ('auth', 'login', 'password', 'otp')):
            return 'auth'
        if any(keyword in text for keyword in ('payment', 'card', 'bank', 'wallet')):
            return 'payment'
        if any(keyword in text for keyword in ('keychain', 'credential', 'secret', 'token')):
            return 'credential'
        return 'general'

    def is_screenshot_ingestion_allowed(self, *, screenshot_enabled: bool, active_app_name: str | None, active_window_title: str | None) -> tuple[bool, str]:
        if not screenshot_enabled:
            return False, 'screenshot_disabled'
        if active_app_name and active_app_name in self._blacklisted_apps:
            return False, 'blacklisted_app'
        scene = self.classify_scene_type(active_app_name=active_app_name, active_window_title=active_window_title)
        if scene in self._blocked_scene_types:
            return False, f'blocked_scene:{scene}'
        return True, 'allowed'

    def should_consider_proactive_message(
        self,
        *,
        active_app_name: str | None,
        user_is_actively_typing: bool,
        observation_confidence: float,
        now_ts: float,
    ) -> bool:
        if not self._proactive_enabled:
            return False
        if user_is_actively_typing:
            return False
        if active_app_name and active_app_name in self._blacklisted_apps:
            return False
        if observation_confidence < 0.55:
            return False
        if now_ts - self._last_proactive_ts < self._cooldown_seconds:
            return False
        return True

    def mark_proactive_emitted(self, *, now_ts: float) -> None:
        self._last_proactive_ts = now_ts
