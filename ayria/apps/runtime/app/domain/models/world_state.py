"""World state models.

This is the heart of the product.
The assistant should not rely only on the last user message. It should respond
based on a synthesized view of the current situation.
"""

from pydantic import BaseModel, Field
from typing import Literal


class ActiveWindow(BaseModel):
    app_name: str
    window_title: str
    url: str | None = None
    bundle_id: str | None = None


class ClipboardState(BaseModel):
    text_preview: str | None = None
    updated_at: str


class ScreenshotSummary(BaseModel):
    image_id: str
    summary: str
    detected_entities: list[str] = Field(default_factory=list)
    scene_type: Literal['code', 'browser', 'document', 'chat', 'image', 'desktop', 'unknown'] = 'unknown'
    confidence: float = 0.0
    analysis_mode: str | None = None
    analysis_provider: str | None = None
    analysis_model: str | None = None


class PresenceState(BaseModel):
    mode: Literal['idle', 'observing', 'chatting', 'busy', 'sleeping']
    user_active: bool
    last_user_input_at: str
    proactive_allowed: bool


class WorldState(BaseModel):
    active_window: ActiveWindow | None = None
    clipboard: ClipboardState | None = None
    recent_screenshots: list[ScreenshotSummary] = Field(default_factory=list)
    recent_messages: list[str] = Field(default_factory=list)
    current_task_hint: str | None = None
    presence: PresenceState | None = None
    user_goal_summary: str | None = None
