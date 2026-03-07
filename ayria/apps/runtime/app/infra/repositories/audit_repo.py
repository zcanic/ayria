from datetime import datetime, timezone
from threading import Lock

from app.domain.models.audit import AuditRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditRepository:
    def __init__(self) -> None:
        self._items: list[AuditRecord] = []
        self._seq = 0
        self._lock = Lock()

    def append(self, *, category: str, action: str, decision: str, summary: str, metadata: dict | None = None) -> AuditRecord:
        with self._lock:
            self._seq += 1
            record = AuditRecord(
                id=f'audit_{self._seq:06d}',
                category=category,
                action=action,
                decision=decision,
                summary=summary,
                metadata=metadata or {},
                created_at=_now_iso(),
            )
            self._items.append(record)
            return record.model_copy(deep=True)

    def list_recent(self, limit: int = 50) -> list[AuditRecord]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._items[-limit:]][::-1]
