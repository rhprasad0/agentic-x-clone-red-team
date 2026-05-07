PUBLIC_EVIDENCE_SCOPE = "validation_runs"
PUBLIC_EVIDENCE_REDACTION_MODE = "synthetic_redacted"
PUBLIC_EVIDENCE_GENERATED_AT = "2026-05-07T00:00:00Z"
PUBLIC_EVIDENCE_TOP_LEVEL_FIELDS = (
    "export_type",
    "scope",
    "redaction_mode",
    "generated_at",
    "safety_notes",
    "validation_runs",
)
PUBLIC_VALIDATION_RUN_FIELDS = (
    "id",
    "scenario_id",
    "status",
    "objective",
    "created_at",
    "events",
    "findings",
)
PUBLIC_VALIDATION_EVENT_FIELDS = (
    "id",
    "validation_run_id",
    "event_type",
    "redacted_summary",
    "created_at",
)
PUBLIC_FINDING_FIELDS = (
    "id",
    "validation_run_id",
    "scenario_run_id",
    "severity",
    "status",
    "title",
    "affected_route_class",
    "affected_object_class",
    "redacted_evidence_summary",
    "fix_ref",
    "regression_ref",
    "residual_risk",
    "created_at",
)


def ordered_public_payload(payload: dict, fields: tuple[str, ...]) -> dict:
    return {field: payload[field] for field in fields}
