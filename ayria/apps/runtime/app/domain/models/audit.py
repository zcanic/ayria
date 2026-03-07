from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    id: str
    category: str
    action: str
    decision: str
    summary: str
    metadata: dict = Field(default_factory=dict)
    created_at: str
