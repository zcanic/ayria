"""Ollama adapter placeholder.

Implement against Ollama's OpenAI-compatible or native API, but normalize the
result into the runtime's provider abstraction.
"""

import httpx


class OllamaProvider:
    provider_id = 'ollama'
    implemented = True

    def __init__(self, base_url: str = 'http://127.0.0.1:11434') -> None:
        self._base_url = base_url.rstrip('/')

    async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
        payload = {
            'model': model,
            'messages': messages,
            'stream': False,
        }
        if tools:
            payload['tools'] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f'{self._base_url}/api/chat', json=payload)
            response.raise_for_status()
            body = response.json()

        message = body.get('message', {})
        content = message.get('content')
        if not isinstance(content, str):
            raise RuntimeError('provider_invalid_output:ollama')

        return {
            'provider': 'ollama',
            'model': model,
            'message': content,
            'tools_used': body.get('tool_calls', tools or []),
        }

    async def health_check(self, model: str | None = None) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f'{self._base_url}/api/tags')
            response.raise_for_status()
            body = response.json()

        models = body.get('models', [])
        available_model_names = {item.get('name') for item in models if isinstance(item, dict)}
        if model is None:
            status = 'ok'
        elif model in available_model_names:
            status = 'ok'
        else:
            status = 'model_not_pulled'

        return {
            'configured': model is not None,
            'implemented': True,
            'reachable': True,
            'status': status,
            'available_models': sorted(name for name in available_model_names if isinstance(name, str)),
        }
