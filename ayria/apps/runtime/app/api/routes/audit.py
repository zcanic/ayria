from fastapi import APIRouter

from app.runtime_container import container

router = APIRouter(prefix='/audit', tags=['audit'])


@router.get('/logs')
def list_audit_logs(limit: int = 25) -> dict:
    items = [record.model_dump() for record in container.audit_repo.list_recent(limit=max(1, min(limit, 200)))]
    return {'items': items}
