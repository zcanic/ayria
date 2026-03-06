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
