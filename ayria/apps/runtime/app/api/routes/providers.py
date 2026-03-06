"""Provider inventory endpoints.

The UI will eventually use these routes to show which local and cloud model
providers are configured and healthy.
"""

from fastapi import APIRouter

from app.runtime_container import container

router = APIRouter(prefix='/providers', tags=['providers'])


@router.get('')
def list_providers() -> dict:
    items = [
        {
            'id': 'ollama',
            'enabled': True,
            'default_model': container.config.capability_model,
            'status': 'unknown',
        },
        {
            'id': 'mlx',
            'enabled': True,
            'default_model': container.config.persona_model,
            'status': 'unknown',
        },
        {
            'id': 'cloud',
            'enabled': container.config.fallback_provider is not None,
            'default_model': container.config.fallback_model,
            'status': 'unknown',
        },
    ]
    return {'items': items}
