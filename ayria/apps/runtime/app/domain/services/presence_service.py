"""Presence service.

This service decides whether the assistant should feel present without becoming
annoying. That means throttling, cooldowns, app blacklists, and user activity
awareness belong here.

This service is where product quality and annoyance risk meet.
If a future agent starts scattering cooldown checks in UI code, route files, or
prompt text, bring those rules back here.
"""

from datetime import datetime, timezone

from app.domain.models.world_state import PresenceState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PresenceService:
    def __init__(
        self,
        proactive_enabled: bool = False,
        cooldown_seconds: int = 300,
        blacklisted_apps: list[str] | None = None,
        blocked_scene_types: list[str] | None = None,
        last_proactive_ts: float = 0.0,
    ) -> None:
        self._proactive_enabled = proactive_enabled
        self._cooldown_seconds = cooldown_seconds
        self._blacklisted_apps = set(blacklisted_apps or [])
        self._blocked_scene_types = {item.lower() for item in (blocked_scene_types or [])}
        self._last_proactive_ts = last_proactive_ts

    @property
    def last_proactive_ts(self) -> float:
        return self._last_proactive_ts

    def cooldown_remaining_seconds(self, *, now_ts: float) -> int:
        if not self._proactive_enabled:
            return 0
        remaining = int(self._cooldown_seconds - (now_ts - self._last_proactive_ts))
        return max(0, remaining)

    def build_presence_state(self, *, mode: str, user_active: bool, reason: str | None = None, focus_label: str | None = None, now_ts: float | None = None) -> PresenceState:
        current_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
        return PresenceState(
            mode=mode,
            user_active=user_active,
            last_user_input_at=_now_iso(),
            proactive_allowed=self._proactive_enabled,
            reason=reason,
            focus_label=focus_label,
            cooldown_remaining_seconds=self.cooldown_remaining_seconds(now_ts=current_ts),
        )

    def presence_for_window(self, *, active_app_name: str | None, active_window_title: str | None) -> PresenceState:
        focus = ' / '.join([item for item in [active_app_name, active_window_title] if item]) or None
        return self.build_presence_state(mode='idle', user_active=True, reason='window_context_updated', focus_label=focus)

    def presence_for_observation(self, *, active_app_name: str | None, active_window_title: str | None) -> PresenceState:
        focus = ' / '.join([item for item in [active_app_name, active_window_title] if item]) or None
        return self.build_presence_state(mode='observing', user_active=True, reason='screenshot_ingested', focus_label=focus)

    def presence_for_user_message(self, *, active_window_title: str | None) -> PresenceState:
        return self.build_presence_state(
            mode='chatting',
            user_active=True,
            reason='user_message_received',
            focus_label=active_window_title,
        )

    def presence_for_tool_activity(self, *, tool_name: str) -> PresenceState:
        return self.build_presence_state(mode='busy', user_active=True, reason='tool_execution', focus_label=tool_name)

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
