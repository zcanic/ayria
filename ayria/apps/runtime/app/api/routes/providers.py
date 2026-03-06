"""Provider inventory endpoints.

The UI will eventually use these routes to show which local and cloud model
providers are configured and healthy.
"""

from fastapi import APIRouter

from app.runtime_container import container

router = APIRouter(prefix='/providers', tags=['providers'])


def _provider_row(provider_id: str, default_model: str | None, configured: bool) -> dict:
    provider = container.llm_providers.get(provider_id)
    implemented = bool(getattr(provider, 'implemented', False)) if provider is not None else False
    runtime_mode = 'stub' if container.config.provider_stub_mode else 'live'
    active_in_runtime_mode = runtime_mode == 'live' and container.config.default_provider == provider_id and configured and implemented
    if runtime_mode == 'stub':
        reachable = False
        reachability_reason = 'stub_mode'
    elif not implemented:
        reachable = False
        reachability_reason = 'not_implemented'
    else:
        reachable = False
        reachability_reason = 'not_probed'

    return {
        'id': provider_id,
        'default_model': default_model,
        'configured': configured,
        'implemented': implemented,
        'reachable': reachable,
        'active_in_runtime_mode': active_in_runtime_mode,
        'runtime_mode': runtime_mode,
        'reachability_reason': reachability_reason,
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
