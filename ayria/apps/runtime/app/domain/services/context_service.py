"""Context aggregation service.

This service turns raw signals into a compact model-facing context.
Weak agents should extend this file instead of concatenating random strings in
multiple places.

Expected long-term inputs:
- active window metadata
- recent screenshot summaries
- recent conversation messages
- selected memory items
- current task intent

Expected long-term outputs:
- full WorldState for debug and orchestration
- compact model-facing context packets
"""

from app.domain.models.world_state import WorldState
from app.infra.repositories.message_repo import MessageRepository
from app.infra.repositories.world_state_repo import WorldStateRepository


class ContextService:
    def __init__(self, world_state_repo: WorldStateRepository, message_repo: MessageRepository) -> None:
        self._world_state_repo = world_state_repo
        self._message_repo = message_repo

    def build_world_state(self) -> WorldState:
        state = self._world_state_repo.get()
        state.recent_messages = self._message_repo.list_recent_for_context()
        return state
