"""Cloud fallback provider placeholder.

Only use this for explicitly allowed scenarios.
The runtime must be able to explain why a request left the local machine.
"""

class CloudProvider:
    implemented = False

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        return {
            'provider': 'cloud',
            'model': model,
            'message': 'stub response',
            'tools_used': tools or [],
        }
