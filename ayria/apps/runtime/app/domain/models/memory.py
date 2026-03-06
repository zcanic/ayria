from pydantic import BaseModel, Field
from typing import Literal


class MemoryItem(BaseModel):
    id: str
    kind: Literal['preference', 'fact', 'relationship', 'habit', 'task_context']
    content: str
    tags: list[str] = Field(default_factory=list)
    salience: float
    created_at: str
    last_used_at: str
