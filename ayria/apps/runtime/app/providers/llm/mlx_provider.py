"""MLX adapter placeholder.

The preferred pattern is to hide MLX behind an OpenAI-compatible adapter service
so the runtime can treat it similarly to other providers.
"""

class MLXProvider:
    provider_id = 'mlx'
    implemented = False
    supports_images = False

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        raise RuntimeError('provider_not_implemented:mlx')

    async def health_check(self, model: str | None = None) -> dict:
        return {
            'configured': model is not None,
            'implemented': False,
            'reachable': False,
            'status': 'not_implemented',
        }
