from app.core.config import AppConfig
from app.domain.services.context_service import ContextService
from app.domain.services.model_execution_service import ModelExecutionService
from app.domain.services.orchestrator import Orchestrator
from app.domain.services.persona_service import PersonaService
from app.domain.services.presence_service import PresenceService
from app.domain.services.routing_service import RoutingService
from app.domain.services.task_service import TaskService
from app.infra.repositories.message_repo import MessageRepository
from app.infra.repositories.task_repo import TaskRepository
from app.infra.repositories.world_state_repo import WorldStateRepository
from app.providers.vision.screenshot_analyzer import ScreenshotAnalyzer
from app.providers.llm.cloud_provider import CloudProvider
from app.providers.llm.mlx_provider import MLXProvider
from app.providers.llm.ollama_provider import OllamaProvider


class RuntimeContainer:
    def __init__(self) -> None:
        self.config = AppConfig()

        self.world_state_repo = WorldStateRepository()
        self.task_repo = TaskRepository()
        self.message_repo = MessageRepository()
        self.llm_providers = {
            'ollama': OllamaProvider(),
            'mlx': MLXProvider(),
            'cloud': CloudProvider(),
        }

        self.task_service = TaskService(self.task_repo)
        self.context_service = ContextService(self.world_state_repo)
        self.presence_service = PresenceService(
            proactive_enabled=self.config.proactive_enabled,
            cooldown_seconds=self.config.proactive_cooldown_seconds,
            blacklisted_apps=self.config.blacklisted_apps,
            blocked_scene_types=self.config.screenshot_blocked_scene_types,
        )
        self.routing_service = RoutingService(default_chat_model=self.config.capability_model)
        self.persona_service = PersonaService()
        self.model_execution_service = ModelExecutionService(
            provider_stub_mode=self.config.provider_stub_mode,
            providers=self.llm_providers,
        )
        self.screenshot_analyzer = ScreenshotAnalyzer()

        self.orchestrator = Orchestrator(
            task_service=self.task_service,
            context_service=self.context_service,
            routing_service=self.routing_service,
            persona_service=self.persona_service,
            model_execution_service=self.model_execution_service,
            presence_service=self.presence_service,
            message_repo=self.message_repo,
            world_state_repo=self.world_state_repo,
        )

    def apply_config(self, next_config: AppConfig) -> None:
        self.config = next_config
        self.routing_service = RoutingService(default_chat_model=self.config.capability_model)
        self.presence_service = PresenceService(
            proactive_enabled=self.config.proactive_enabled,
            cooldown_seconds=self.config.proactive_cooldown_seconds,
            blacklisted_apps=self.config.blacklisted_apps,
            blocked_scene_types=self.config.screenshot_blocked_scene_types,
        )
        self.model_execution_service = ModelExecutionService(
            provider_stub_mode=self.config.provider_stub_mode,
            providers=self.llm_providers,
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
        )


container = RuntimeContainer()
