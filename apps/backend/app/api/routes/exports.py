from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.api.dto import export_dto
from app.core.auth import ActorContext
from app.services.authorization import export_invocation
from app.services.evidence_exports import (
    PUBLIC_EVIDENCE_REDACTION_MODE,
    PUBLIC_EVIDENCE_SCOPE,
    build_public_evidence_export,
)

router = APIRouter(tags=["exports"])


class PublicEvidenceExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["validation_runs"] = PUBLIC_EVIDENCE_SCOPE
    validation_run_ids: list[str] | None = None
    redaction_mode: Literal["synthetic_redacted"] = PUBLIC_EVIDENCE_REDACTION_MODE


@router.post("/exports/public-evidence")
def export_public_evidence(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    response: Response,
    request: Annotated[
        PublicEvidenceExportRequest | None,
        Body(),
    ] = None,
) -> dict[str, Any]:
    request = request or PublicEvidenceExportRequest()
    export_invocation(actor)
    response.headers["Cache-Control"] = "no-store"
    return export_dto(
        build_public_evidence_export(
            db,
            validation_run_ids=request.validation_run_ids,
            redaction_mode=request.redaction_mode,
        )
    )
