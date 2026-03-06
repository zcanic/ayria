"""Provider inventory endpoints.

The UI will eventually use these routes to show which local and cloud model
providers are configured and healthy.
"""

from fastapi import APIRouter
import asyncio

from app.runtime_container import container

router = APIRouter(prefix='/providers', tags=['providers'])


def _provider_row(provider_id: str, default_model: str | None, configured: bool) -> dict:
    provider = container.llm_providers.get(provider_id)
    implemented = bool(getattr(provider, 'implemented', False)) if provider is not None else False
    runtime_mode = 'stub' if container.config.provider_stub_mode else 'live'
    if runtime_mode == 'stub':
        health = {
            'configured': configured,
            'implemented': implemented,
            'reachable': False,
            'status': 'stub_mode',
        }
    else:
        health = asyncio.run(
            container.model_execution_service.check_provider_health(provider_name=provider_id, model=default_model)
        )
    active_in_runtime_mode = runtime_mode == 'live' and container.config.default_provider == provider_id and configured and implemented

    return {
        'id': provider_id,
        'default_model': default_model,
        'configured': health.get('configured', configured),
        'implemented': health.get('implemented', implemented),
        'reachable': health.get('reachable', False),
        'active_in_runtime_mode': active_in_runtime_mode,
        'runtime_mode': runtime_mode,
        'status': health.get('status', 'unknown'),
    }


@router.get('')
def list_providers() -> dict:
    items = [
        _provider_row('ollama', container.config.capability_model, configured=container.config.capability_model is not None),
        _provider_row('mlx', container.config.persona_model, configured=container.config.persona_model is not None),
        _provider_row(
            'cloud',
            container.config.fallback_model,
            configured=container.config.fallback_provider is not None and container.config.fallback_model is not None,
        ),
    ]
    return {'runtime_mode': 'stub' if container.config.provider_stub_mode else 'live', 'items': items}
