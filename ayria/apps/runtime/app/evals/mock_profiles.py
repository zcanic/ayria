"""Built-in mock profiles for deterministic eval scenarios.

These profiles let the eval runner exercise important failure paths without
depending on fragile machine setup changes such as uninstalling a model.
"""

from __future__ import annotations

from app.domain.services.model_execution_service import ModelExecutionService
from app.runtime_container import RuntimeContainer


def apply_mock_profile(container: RuntimeContainer, profile: str) -> None:
    if profile == 'missing_model_ollama':
        class FakeMissingModelProvider:
            implemented = True
            provider_id = 'ollama'

            def normalize_model_name(self, model: str) -> str:
                return model

            async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
                raise AssertionError('chat should not run when model is missing')

            async def health_check(self, model: str | None = None) -> dict:
                return {
                    'configured': True,
                    'implemented': True,
                    'reachable': True,
                    'status': 'model_not_pulled',
                }

        container.llm_providers['ollama'] = FakeMissingModelProvider()
        container.model_execution_service = ModelExecutionService(
            provider_stub_mode=container.config.provider_stub_mode,
            providers=container.llm_providers,
        )
        container.orchestrator._model_execution_service = container.model_execution_service
        return

    raise ValueError(f'unsupported mock profile: {profile}')
