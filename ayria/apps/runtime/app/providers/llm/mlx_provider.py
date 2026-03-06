"""MLX adapter placeholder.

The preferred pattern is to hide MLX behind an OpenAI-compatible adapter service
so the runtime can treat it similarly to other providers.
"""

class MLXProvider:
    implemented = False

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        return {
            'provider': 'mlx',
            'model': model,
            'message': 'stub response',
            'tools_used': tools or [],
        }
