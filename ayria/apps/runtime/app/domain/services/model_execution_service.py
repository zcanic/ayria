from __future__ import annotations

import base64
from pathlib import Path

from app.providers.llm.base import LLMProvider


class ModelExecutionService:
    def __init__(self, provider_stub_mode: bool, providers: dict[str, LLMProvider]) -> None:
        self._provider_stub_mode = provider_stub_mode
        self._providers = providers

    @property
    def provider_stub_mode(self) -> bool:
        return self._provider_stub_mode

    def _resolve_provider(self, provider_name: str) -> LLMProvider:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise RuntimeError(f'provider_unavailable:{provider_name}')
        if not bool(getattr(provider, 'implemented', False)):
            raise RuntimeError(f'provider_not_implemented:{provider_name}')
        return provider

    def _encode_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise RuntimeError(f'image_not_found:{image_path}')
        if not path.is_file():
            raise RuntimeError(f'image_not_file:{image_path}')
        try:
            return base64.b64encode(path.read_bytes()).decode('ascii')
        except Exception as error:
            raise RuntimeError(f'image_read_failed:{image_path}:{error}') from error

    def _build_messages(self, *, text: str, image_paths: list[str] | None) -> list[dict]:
        message: dict[str, object] = {'role': 'user', 'content': text}
        if image_paths:
            message['images'] = [self._encode_image(path) for path in image_paths]
        return [message]

    async def run_chat(
        self,
        *,
        provider_name: str,
        model: str,
        text: str,
        image_paths: list[str] | None = None,
    ) -> dict:
        provider = self._resolve_provider(provider_name)
        resolved_model = model
        normalize_model_name = getattr(provider, 'normalize_model_name', None)
        if callable(normalize_model_name):
            resolved_model = str(normalize_model_name(model))

        if image_paths and not bool(getattr(provider, 'supports_images', False)):
            raise RuntimeError(f'provider_does_not_support_images:{provider_name}')

        health = await self.check_provider_health(provider_name=provider_name, model=resolved_model)
        health_status = str(health.get('status', ''))
        if health_status == 'model_not_pulled':
            raise RuntimeError(
                f"model_not_pulled:{provider_name}:{resolved_model}:Install it first with `ollama pull {resolved_model}`"
            )
        if health_status.startswith('error:'):
            raise RuntimeError(health_status.split(':', 1)[1])
        if health_status not in {'', 'ok'}:
            raise RuntimeError(f'provider_health_not_ok:{provider_name}:{health_status}')

        messages = self._build_messages(text=text, image_paths=image_paths)
        return await provider.chat(messages=messages, model=resolved_model, tools=None)

    async def check_provider_health(self, *, provider_name: str, model: str | None) -> dict:
        provider = self._providers.get(provider_name)
        if provider is None:
            return {
                'configured': model is not None,
                'implemented': False,
                'supports_images': False,
                'reachable': False,
                'status': 'missing',
            }
        try:
            health = await provider.health_check(model=model)
            if 'supports_images' not in health:
                health['supports_images'] = bool(getattr(provider, 'supports_images', False))
            return health
        except Exception as error:
            return {
                'configured': model is not None,
                'implemented': bool(getattr(provider, 'implemented', False)),
                'supports_images': bool(getattr(provider, 'supports_images', False)),
                'reachable': False,
                'status': f'error:{error}',
            }
