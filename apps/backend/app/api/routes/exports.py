from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_db_session
from app.core.auth import ActorContext, require_harness
from app.services.evidence_exports import build_public_evidence_export

router = APIRouter(tags=["exports"])


@router.post("/exports/public-evidence")
def export_public_evidence(
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    require_harness(actor)
    return build_public_evidence_export(db)
