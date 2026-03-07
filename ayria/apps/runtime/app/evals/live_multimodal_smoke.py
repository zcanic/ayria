"""Run a local live multimodal smoke test against the ayria runtime path.

This command is intentionally separate from standardized eval scenarios because
it depends on a real local model and therefore is not deterministic enough for
CI baselines.

Usage:
`uv run python -m app.evals.live_multimodal_smoke --image /path/to/image.png`
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.runtime_container import RuntimeContainer


def _bind_container(container: RuntimeContainer) -> None:
    import app.api.routes.chat as chat_route
    import app.api.routes.config as config_route
    import app.api.routes.events as events_route
    import app.api.routes.health as health_route
    import app.api.routes.memory as memory_route
    import app.api.routes.providers as providers_route
    import app.api.routes.tasks as tasks_route
    import app.api.routes.tools as tools_route
    import app.api.routes.world_state as world_state_route
    import app.api.routes.ws as ws_route

    chat_route.container = container
    config_route.container = container
    events_route.container = container
    health_route.container = container
    memory_route.container = container
    providers_route.container = container
    tasks_route.container = container
    tools_route.container = container
    world_state_route.container = container
    ws_route.container = container


def main() -> int:
    parser = argparse.ArgumentParser(description='Run a live multimodal smoke test through ayria.')
    parser.add_argument('--image', required=True, help='Path to a local image file')
    parser.add_argument('--prompt', default='What is the dominant color in this image? Answer briefly.', help='Prompt to send with the image')
    parser.add_argument('--model', default='qwen3.5:0.8b', help='Vision-capable model name')
    args = parser.parse_args()

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        print(json.dumps({'ok': False, 'error': f'image_not_found:{image_path}'}, ensure_ascii=False, indent=2))
        return 2

    container = RuntimeContainer()
    next_config = container.config.model_copy(
        update={
            'provider_stub_mode': False,
            'capability_model': args.model,
            'vision_model': args.model,
            'screenshot_analysis_model': args.model,
        }
    )
    container.apply_config(next_config)
    _bind_container(container)
    client = TestClient(app)

    t0 = time.perf_counter()
    response = client.post(
        '/api/v1/chat/send',
        json={
            'text': args.prompt,
            'image_paths': [str(image_path)],
        },
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    body = response.json()
    print(
        json.dumps(
            {
                'ok': response.status_code == 200 and body.get('status') == 'completed',
                'latency_ms': latency_ms,
                'image': str(image_path),
                'model': args.model,
                'response_status': response.status_code,
                'runtime_status': body.get('status'),
                'route': body.get('route'),
                'assistant_text': (((body.get('assistant_message') or {}).get('parts') or [{}])[0]).get('text'),
                'error': body.get('error'),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if response.status_code == 200 and body.get('status') == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
