from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.api.dto import export_dto
from app.core.auth import ActorContext
from app.services.authorization import export_invocation
from app.services.evidence_exports import build_public_evidence_export

router = APIRouter(tags=["exports"])


@router.post("/exports/public-evidence")
def export_public_evidence(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    export_invocation(actor)
    return export_dto(build_public_evidence_export(db))
