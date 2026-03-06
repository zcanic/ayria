"""Chat endpoints.

Do not let this module become the entire application.
It should only translate HTTP requests into orchestrator calls.
Business logic belongs in domain services.

Implementation notes:
- This route should be fast and should acknowledge task creation quickly.
- Long-running model execution should later move to a task runner or async flow.
- The desktop should get rich progress updates through WebSocket, not through
  ever-growing chat route complexity.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.runtime_container import container

router = APIRouter(prefix='/chat', tags=['chat'])


class SendChatRequest(BaseModel):
    text: str = Field(description='Primary user message text')
    image_paths: list[str] = Field(default_factory=list)


@router.post('/send')
def send_chat(request: SendChatRequest) -> dict:
    return container.orchestrator.handle_user_message(text=request.text, image_paths=request.image_paths)
