"""Health endpoints.

These routes are intentionally simple and should be implemented first.
A weak agent can use them to verify that the runtime starts correctly before
attempting model integrations.
"""

from fastapi import APIRouter
import asyncio

from app.runtime_container import container

router = APIRouter()


@router.get('/health')
def get_health() -> dict:
    return {
        'status': 'ok',
        'service': 'ayria-runtime',
        'version': '0.1.0',
    }


@router.get('/health/providers')
def get_provider_health() -> dict:
    runtime_mode = 'stub' if container.config.provider_stub_mode else 'live'

    def provider_status(provider_id: str, model: str | None, configured: bool) -> dict:
        provider = container.llm_providers.get(provider_id)
        implemented = bool(getattr(provider, 'implemented', False)) if provider is not None else False
        supports_images = bool(getattr(provider, 'supports_images', False)) if provider is not None else False
        if runtime_mode == 'stub':
            health = {
                'configured': configured,
                'implemented': implemented,
                'reachable': False,
                'status': 'stub_mode',
            }
        else:
            health = asyncio.run(
                container.model_execution_service.check_provider_health(provider_name=provider_id, model=model)
            )
        active = runtime_mode == 'live' and health.get('configured', configured) and health.get('implemented', implemented) and container.config.default_provider == provider_id
        return {
            'id': provider_id,
            'status': health.get('status', 'unknown'),
            'model': model,
            'configured': health.get('configured', configured),
            'implemented': health.get('implemented', implemented),
            'supports_images': supports_images,
            'reachable': health.get('reachable', False),
            'active_in_runtime_mode': active,
        }

    return {
        'runtime_mode': runtime_mode,
        'providers': [
            provider_status('ollama', container.config.capability_model, configured=container.config.capability_model is not None),
            provider_status('mlx', container.config.persona_model, configured=container.config.persona_model is not None),
            provider_status(
                'cloud',
                container.config.fallback_model,
                configured=container.config.fallback_provider is not None and container.config.fallback_model is not None,
            ),
        ]
    }
