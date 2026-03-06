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
    return {
        'providers': [
            {'id': 'ollama', 'status': 'unknown', 'model': container.config.capability_model},
            {'id': 'mlx', 'status': 'unknown', 'model': container.config.persona_model},
            {'id': 'cloud', 'status': 'unknown', 'model': container.config.fallback_model},
        ]
    }
