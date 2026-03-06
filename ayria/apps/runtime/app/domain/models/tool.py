"""Tool models.

Centralize tool metadata here so providers and agents can reason over a common
shape. This makes tool schemas easier to expose to local models later.
"""

from pydantic import BaseModel


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    requires_confirmation: bool = False
    timeout_seconds: int = 20
