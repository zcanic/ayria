"""LLM provider abstraction.

All model backends should implement the same minimal interface.
Do not let Ollama-specific or MLX-specific request shapes leak into the rest of
runtime code.
"""

from typing import Protocol


class LLMProvider(Protocol):
    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        ...
