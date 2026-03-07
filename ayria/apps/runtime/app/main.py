"""Runtime server entry point.

This service is the actual brain-stem of the product.
Do not reduce it to "just a chat API".

Primary responsibilities:
- receive user and environment events
- maintain world state
- orchestrate tasks
- talk to model providers
- emit assistant updates back to the desktop shell

Development notes for weaker agents:
- Add new HTTP routes under `app/api/routes`, then register them here.
- Do not place orchestration logic in this file.
- Do not import provider-specific code directly here unless it is needed for
  app startup wiring.
- If WebSocket support is added later, keep the connection manager in a
  dedicated module instead of embedding it into route files.

Recommended implementation order:
1. health routes
2. chat send route
3. world-state debug route
4. event ingress
5. websocket event push
"""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.chat import router as chat_router
from app.api.routes.events import router as events_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.memory import router as memory_router
from app.api.routes.config import router as config_router
from app.api.routes.providers import router as providers_router
from app.api.routes.world_state import router as world_state_router
from app.api.routes.tools import router as tools_router
from app.api.routes.ws import router as ws_router
from app.api.routes.audit import router as audit_router

app = FastAPI(title="ayria-runtime", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(providers_router, prefix="/api/v1")
app.include_router(world_state_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
