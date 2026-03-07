from app.providers.llm.base import LLMProvider


class ModelExecutionService:
    def __init__(self, provider_stub_mode: bool, providers: dict[str, LLMProvider]) -> None:
        self._provider_stub_mode = provider_stub_mode
        self._providers = providers

    @property
    def provider_stub_mode(self) -> bool:
        return self._provider_stub_mode

    async def run_chat(self, *, provider_name: str, model: str, text: str) -> dict:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise RuntimeError(f'provider_unavailable:{provider_name}')
        if not bool(getattr(provider, 'implemented', False)):
            raise RuntimeError(f'provider_not_implemented:{provider_name}')
        resolved_model = model
        normalize_model_name = getattr(provider, 'normalize_model_name', None)
        if callable(normalize_model_name):
            resolved_model = str(normalize_model_name(model))
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
        return await provider.chat(messages=[{'role': 'user', 'content': text}], model=resolved_model, tools=None)

    async def check_provider_health(self, *, provider_name: str, model: str | None) -> dict:
        provider = self._providers.get(provider_name)
        if provider is None:
            return {
                'configured': model is not None,
                'implemented': False,
                'reachable': False,
                'status': 'missing',
            }
        try:
            return await provider.health_check(model=model)
        except Exception as error:
            return {
                'configured': model is not None,
                'implemented': bool(getattr(provider, 'implemented', False)),
                'reachable': False,
                'status': f'error:{error}',
            }
