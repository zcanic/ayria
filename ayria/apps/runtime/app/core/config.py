from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    default_provider: str = 'ollama'
    capability_model: str = 'qwen3.5:0.8b'
    vision_provider: str = 'ollama'
    vision_model: str = 'qwen3.5:0.8b'
    screenshot_analysis_provider: str = 'ollama'
    screenshot_analysis_model: str = 'qwen3.5:0.8b'
    persona_model: str | None = None
    fallback_provider: str | None = None
    fallback_model: str | None = None
    proactive_enabled: bool = False
    proactive_cooldown_seconds: int = 300
    screenshot_enabled: bool = True
    screenshot_interval_seconds: int = 0
    blacklisted_apps: list[str] = Field(default_factory=list)
    screenshot_blocked_scene_types: list[str] = Field(default_factory=lambda: ['auth', 'payment', 'credential'])
    persona_intensity: str = 'normal'
    memory_enabled: bool = True
    # Scaffold default: local inference is configured but intentionally disabled
    # until a real provider path is verified.
    provider_stub_mode: bool = True
