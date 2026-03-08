"""Cloud fallback provider placeholder.

Only use this for explicitly allowed scenarios.
The runtime must be able to explain why a request left the local machine.
"""

class CloudProvider:
    provider_id = 'cloud'
    implemented = False
    supports_images = False

    def normalize_model_name(self, model: str) -> str:
        return model

    async def chat(self, messages: list[dict[str, object]], model: str, tools: list[dict[str, object]] | None = None) -> dict[str, object]:
        raise RuntimeError('provider_not_implemented:cloud')

    async def health_check(self, model: str | None = None) -> dict[str, object]:
        return {
            'configured': model is not None,
            'implemented': False,
            'reachable': False,
            'status': 'not_implemented',
        }
