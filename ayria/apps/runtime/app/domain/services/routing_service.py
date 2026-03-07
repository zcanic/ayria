from pydantic import BaseModel

from app.domain.models.world_state import WorldState


class RouteDecision(BaseModel):
    provider: str
    model: str
    use_tools: bool
    use_persona_rewrite: bool
    timeout_seconds: int
    reason: str


class RoutingService:
    def __init__(
        self,
        *,
        default_chat_model: str = 'qwen3.5:0.8b',
        vision_model: str = 'Qwen2.5-VL-3B',
        complex_model: str = 'qwen3.5:9b',
    ) -> None:
        self._default_chat_model = default_chat_model
        self._vision_model = vision_model
        self._complex_model = complex_model

    def choose_for_chat(self, *, has_images: bool, current_world_state: WorldState) -> RouteDecision:
        default_model = self._default_chat_model
        if has_images:
            default_model = self._vision_model
        if current_world_state.current_task_hint and 'complex' in current_world_state.current_task_hint.lower():
            default_model = self._complex_model
        return RouteDecision(
            provider='ollama',
            model=default_model,
            use_tools=False,
            use_persona_rewrite=True,
            timeout_seconds=30,
            reason='local-first chat route with optional multimodal vision input',
        )
