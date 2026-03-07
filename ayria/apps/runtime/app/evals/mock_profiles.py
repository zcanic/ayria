"""Built-in mock profiles for deterministic eval scenarios.

These profiles let the eval runner exercise important failure paths without
depending on fragile machine setup changes such as uninstalling a model.
"""

from __future__ import annotations

from app.domain.services.model_execution_service import ModelExecutionService
from app.providers.vision.screenshot_analyzer import ScreenshotAnalyzer
from app.runtime_container import RuntimeContainer


def apply_mock_profile(container: RuntimeContainer, profile: str) -> None:
    def _rebind_runtime_services() -> None:
        container.model_execution_service = ModelExecutionService(
            provider_stub_mode=container.config.provider_stub_mode,
            providers=container.llm_providers,
        )
        container.orchestrator._model_execution_service = container.model_execution_service
        container.screenshot_analyzer = ScreenshotAnalyzer(
            model_execution_service=container.model_execution_service,
            provider_name=container.config.screenshot_analysis_provider,
            model=container.config.screenshot_analysis_model,
        )

    if profile == 'missing_model_ollama':
        class FakeMissingModelProvider:
            implemented = True
            provider_id = 'ollama'
            supports_images = True

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
        _rebind_runtime_services()
        return

    if profile == 'multimodal_ollama':
        class FakeMultimodalProvider:
            implemented = True
            provider_id = 'ollama'
            supports_images = True

            def normalize_model_name(self, model: str) -> str:
                return model

            async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
                first_message = messages[0]
                image_count = len(first_message.get('images') or [])
                prompt = str(first_message.get('content', ''))
                if 'desktop-assistant context' in prompt:
                    return {
                        'provider': 'ollama',
                        'model': model,
                        'message': 'A browser screenshot showing the Ayria docs page and a visible navigation sidebar.',
                    }
                return {
                    'provider': 'ollama',
                    'model': model,
                    'message': f'multimodal-ok:{image_count}',
                }

            async def health_check(self, model: str | None = None) -> dict:
                return {
                    'configured': True,
                    'implemented': True,
                    'reachable': True,
                    'status': 'ok',
                    'supports_images': True,
                }

        container.llm_providers['ollama'] = FakeMultimodalProvider()
        _rebind_runtime_services()
        return

    raise ValueError(f'unsupported mock profile: {profile}')
