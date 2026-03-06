"""Domain event models.

ayria is event-driven. If a future agent starts bypassing events and directly
mutating state from random places, that should be treated as architectural debt.
"""

from pydantic import BaseModel
from typing import Literal


class DomainEvent(BaseModel):
    id: str
    type: str
    source: Literal['desktop', 'runtime', 'system', 'tool', 'model']
    timestamp: str
    payload: dict
