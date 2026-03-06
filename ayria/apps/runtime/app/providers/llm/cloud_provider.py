"""Cloud fallback provider placeholder.

Only use this for explicitly allowed scenarios.
The runtime must be able to explain why a request left the local machine.
"""

class CloudProvider:
    provider_id = 'cloud'
    implemented = False

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        raise RuntimeError('provider_not_implemented:cloud')

    async def health_check(self, model: str | None = None) -> dict:
        return {
            'configured': model is not None,
            'implemented': False,
            'reachable': False,
            'status': 'not_implemented',
        }
