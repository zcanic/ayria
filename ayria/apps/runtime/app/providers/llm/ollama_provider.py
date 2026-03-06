"""Ollama adapter placeholder.

Implement against Ollama's OpenAI-compatible or native API, but normalize the
result into the runtime's provider abstraction.
"""

class OllamaProvider:
    implemented = False

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        return {
            'provider': 'ollama',
            'model': model,
            'message': 'stub response',
            'tools_used': tools or [],
        }
