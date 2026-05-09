from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.api.dto import export_dto
from app.core.auth import ActorContext
from app.core.logging_config import emit_operational_event
from app.core.security_logging import emit_security_event, v2_route_metadata
from app.services.authorization import export_invocation
from app.services.evidence_exports import (
    PUBLIC_EVIDENCE_REDACTION_MODE,
    PUBLIC_EVIDENCE_SCOPE,
    build_public_evidence_export,
)

router = APIRouter(tags=["exports"])


class PublicEvidenceExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["validation_runs"] = cast(Literal["validation_runs"], PUBLIC_EVIDENCE_SCOPE)
    validation_run_ids: list[str] | None = None
    redaction_mode: Literal["synthetic_redacted"] = cast(
        Literal["synthetic_redacted"], PUBLIC_EVIDENCE_REDACTION_MODE
    )


@router.post("/exports/public-evidence")
@v2_route_metadata(
    auth_class="harness", route_class="export", target_object_class="public_evidence_export"
)
def export_public_evidence(
    http_request: Request,
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
    response_json = export_dto(
        build_public_evidence_export(
            db,
            validation_run_ids=request.validation_run_ids,
            redaction_mode=request.redaction_mode,
        )
    )
    emit_security_event(
        http_request,
        event_class="export_invocation",
        status_code=200,
        outcome_class="success",
        actor=actor,
    )
    emit_operational_event(
        http_request,
        event_class="export_write",
        outcome_class="success",
        actor=actor,
        status_code=200,
        artifact_path_class="public_evidence_export",
        item_count=(
            len(response_json.get("validation_runs", []))
            if isinstance(response_json, dict)
            else 0
        ),
    )
    return response_json
