"""MLX adapter placeholder.

The preferred pattern is to hide MLX behind an OpenAI-compatible adapter service
so the runtime can treat it similarly to other providers.
"""

class MLXProvider:
    provider_id = 'mlx'
    implemented = False
    supports_images = False

    def normalize_model_name(self, model: str) -> str:
        return model

    async def chat(self, messages: list[dict[str, object]], model: str, tools: list[dict[str, object]] | None = None) -> dict[str, object]:
        raise RuntimeError('provider_not_implemented:mlx')

    async def health_check(self, model: str | None = None) -> dict[str, object]:
        return {
            'configured': model is not None,
            'implemented': False,
            'reachable': False,
            'status': 'not_implemented',
        }
