from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.security_logging import emit_security_event

ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "request_too_large",
    422: "validation_error",
    429: "resource_limit",
}

PROTECTED_REQUEST_FIELDS = frozenset(
    {
        "id",
        "author_agent_id",
        "actor_id",
        "owner_id",
        "authority_type",
        "role",
        "token",
        "token_hash",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "metadata_json",
        "raw_trace",
        "raw_body",
        "request_body",
        "response_body",
        "request_headers",
        "authorization",
        "status",
        "like_count",
        "quote_count",
        "repost_count",
        "reply_count",
        "follower_count",
        "following_count",
        "root_post_id",
        "parent_post_id",
        "reply_depth",
        "validation_run_id",
        "scenario_run_id",
        "environment_value",
        "private_path",
        "sql_fragment",
        "stack_trace",
        "dependency_url",
    }
)

MUTATION_METHODS = {"DELETE", "PATCH", "POST", "PUT"}

SAFE_MESSAGES = {
    400: "Bad request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Resource not found",
    409: "Conflict",
    413: "Request body is too large",
    422: "Request validation failed",
    429: "Resource limit reached",
}


def error_response(
    status_code: int,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": ERROR_CODES.get(status_code, "error"),
                "message": message or SAFE_MESSAGES.get(status_code, "Request failed"),
                "details": details,
            }
        },
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        if _has_protected_field_rejection(exc):
            emit_security_event(
                request,
                event_class="protected_field_rejection",
                status_code=422,
                outcome_class="denied",
            )
        emit_security_event(
            request,
            event_class="schema_validation_failure",
            status_code=422,
            outcome_class="denied",
        )
        return error_response(422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        event_class = _security_event_for_http_exception(request, exc)
        if event_class is not None:
            emit_security_event(
                request,
                event_class=event_class,
                status_code=exc.status_code,
                outcome_class="denied",
            )
        return error_response(
            exc.status_code,
            SAFE_MESSAGES.get(exc.status_code),
            headers=dict(exc.headers or {}),
        )


def _has_protected_field_rejection(exc: RequestValidationError) -> bool:
    for error in exc.errors():
        loc = error.get("loc", ())
        if not loc:
            continue
        field_name = str(loc[-1]).lower()
        if field_name in PROTECTED_REQUEST_FIELDS:
            return True
    return False


def _security_event_for_http_exception(
    request: Request, exc: StarletteHTTPException
) -> str | None:
    if exc.status_code == 400 and "cursor" in request.query_params:
        return "cursor_tamper_or_expiry"
    if exc.status_code == 409 and request.method in MUTATION_METHODS:
        return "idempotency_conflict"
    if exc.status_code == 422:
        return "schema_validation_failure"
    if exc.status_code == 429:
        return "guardrail_limit"
    if exc.status_code == 404 and _route_has_object_identifier(request):
        return "object_authorization_denied"
    return None


def _route_has_object_identifier(request: Request) -> bool:
    endpoint = request.scope.get("endpoint")
    target_object_class = getattr(endpoint, "v2_target_object_class", None)
    return isinstance(target_object_class, str) and target_object_class not in {
        "health",
        "timeline",
    }
