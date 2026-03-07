from app.core.config import AppConfig
from app.domain.services.context_service import ContextService
from app.domain.services.model_execution_service import ModelExecutionService
from app.domain.services.orchestrator import Orchestrator
from app.domain.services.persona_service import PersonaService
from app.domain.services.presence_service import PresenceService
from app.domain.services.routing_service import RoutingService
from app.domain.services.task_service import TaskService
from app.domain.services.tool_service import ToolService
from app.infra.repositories.message_repo import MessageRepository
from app.infra.repositories.task_repo import TaskRepository
from app.infra.repositories.world_state_repo import WorldStateRepository
from app.providers.vision.screenshot_analyzer import ScreenshotAnalyzer
from app.providers.llm.cloud_provider import CloudProvider
from app.providers.llm.mlx_provider import MLXProvider
from app.providers.llm.ollama_provider import OllamaProvider
from app.providers.tools.registry import ToolRegistry
from app.realtime.event_stream import EventStream


class RuntimeContainer:
    def __init__(self) -> None:
        self.config = AppConfig()

        self.world_state_repo = WorldStateRepository()
        self.task_repo = TaskRepository()
        self.message_repo = MessageRepository()
        self.event_stream = EventStream()
        self.llm_providers = {
            'ollama': OllamaProvider(),
            'mlx': MLXProvider(),
            'cloud': CloudProvider(),
        }
        self.tool_registry = ToolRegistry()

        self.task_service = TaskService(self.task_repo)
        self.context_service = ContextService(self.world_state_repo, self.message_repo)
        self.presence_service = self._build_presence_service(last_proactive_ts=0.0)
        self.routing_service = RoutingService(
            default_chat_model=self.config.capability_model,
            vision_model=self.config.vision_model,
            complex_model=self.config.fallback_model or 'qwen3.5:9b',
        )
        self.persona_service = PersonaService()
        self.tool_service = ToolService(self.tool_registry, world_state_repo=self.world_state_repo)
        self.model_execution_service = ModelExecutionService(
            provider_stub_mode=self.config.provider_stub_mode,
            providers=self.llm_providers,
        )
        self.screenshot_analyzer = ScreenshotAnalyzer(
            model_execution_service=self.model_execution_service,
            provider_name=self.config.screenshot_analysis_provider,
            model=self.config.screenshot_analysis_model,
        )

        self.orchestrator = Orchestrator(
            task_service=self.task_service,
            context_service=self.context_service,
            routing_service=self.routing_service,
            persona_service=self.persona_service,
            model_execution_service=self.model_execution_service,
            presence_service=self.presence_service,
            message_repo=self.message_repo,
            world_state_repo=self.world_state_repo,
            event_stream=self.event_stream,
        )

    def apply_config(self, next_config: AppConfig) -> None:
        last_proactive_ts = self.presence_service.last_proactive_ts
        self.config = next_config
        self.routing_service = RoutingService(
            default_chat_model=self.config.capability_model,
            vision_model=self.config.vision_model,
            complex_model=self.config.fallback_model or 'qwen3.5:9b',
        )
        self.presence_service = self._build_presence_service(last_proactive_ts=last_proactive_ts)
        self.model_execution_service = ModelExecutionService(
            provider_stub_mode=self.config.provider_stub_mode,
            providers=self.llm_providers,
        )
        self.screenshot_analyzer = ScreenshotAnalyzer(
            model_execution_service=self.model_execution_service,
            provider_name=self.config.screenshot_analysis_provider,
            model=self.config.screenshot_analysis_model,
        )
        self.orchestrator = Orchestrator(
            task_service=self.task_service,
            context_service=self.context_service,
            routing_service=self.routing_service,
            persona_service=self.persona_service,
            model_execution_service=self.model_execution_service,
            presence_service=self.presence_service,
            message_repo=self.message_repo,
            world_state_repo=self.world_state_repo,
            event_stream=self.event_stream,
        )

    def _build_presence_service(self, *, last_proactive_ts: float) -> PresenceService:
        return PresenceService(
            proactive_enabled=self.config.proactive_enabled,
            cooldown_seconds=self.config.proactive_cooldown_seconds,
            blacklisted_apps=self.config.blacklisted_apps,
            blocked_scene_types=self.config.screenshot_blocked_scene_types,
            last_proactive_ts=last_proactive_ts,
        )


container = RuntimeContainer()
