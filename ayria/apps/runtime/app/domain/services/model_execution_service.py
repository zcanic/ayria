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
        return await provider.chat(messages=[{'role': 'user', 'content': text}], model=model, tools=None)

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
