"""Chat endpoints.

Do not let this module become the entire application.
It should only translate HTTP requests into orchestrator calls.
Business logic belongs in domain services.

Implementation notes:
- In the current v1 scaffold, this route is synchronous by contract.
- It still creates a task record for observability, but returns the final
  result in the same request.
- If background task execution is introduced later, update code and docs
  together rather than leaving a half-synchronous API contract.
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
