"""LLM provider abstraction.

All model backends should implement the same minimal interface.
Do not let Ollama-specific or MLX-specific request shapes leak into the rest of
runtime code.
"""

from typing import Protocol


class LLMProvider(Protocol):
    provider_id: str
    implemented: bool

    def normalize_model_name(self, model: str) -> str:
        ...

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        ...

    async def health_check(self, model: str | None = None) -> dict:
        ...
