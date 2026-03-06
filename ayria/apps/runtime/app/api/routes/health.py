"""Health endpoints.

These routes are intentionally simple and should be implemented first.
A weak agent can use them to verify that the runtime starts correctly before
attempting model integrations.
"""

from fastapi import APIRouter

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
        active = runtime_mode == 'live' and configured and implemented and container.config.default_provider == provider_id
        if runtime_mode == 'stub':
            status = 'stub_mode'
        elif not configured:
            status = 'not_configured'
        elif not implemented:
            status = 'not_implemented'
        else:
            status = 'not_probed'
        return {
            'id': provider_id,
            'status': status,
            'model': model,
            'configured': configured,
            'implemented': implemented,
            'reachable': False,
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
