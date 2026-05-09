import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routes import (
    agents,
    exports,
    fixtures,
    posts,
    relationships,
    scenario_runs,
    timeline,
    validation_runs,
)
from app.core.config import Settings, get_settings
from app.core.logging_config import configure_logging, emit_operational_event
from app.core.security_logging import v2_route_metadata

health_router = APIRouter(tags=["health"])

NO_STORE_EXACT_ROUTES = {
    ("POST", "/agents/signup"),
    ("GET", "/timelines/home"),
}
NO_STORE_PREFIXES = (
    "/exports/",
    "/findings",
    "/fixtures",
    "/scenario-runs",
    "/validation-runs",
)
SECURITY_SENSITIVE_ERROR_STATUSES = {401, 403, 422}
MUTATION_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
BROWSER_CORS_READ_METHODS = ["GET", "HEAD"]


@health_router.get("/health")
@v2_route_metadata(auth_class="public", route_class="health", target_object_class="health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


def register_routes(app: FastAPI) -> None:
    """Register API routes; future route modules should be included here."""

    app.include_router(health_router)
    app.include_router(agents.router)
    app.include_router(timeline.router)
    app.include_router(posts.router)
    app.include_router(relationships.router)
    app.include_router(validation_runs.router)
    app.include_router(validation_runs.finding_router)
    app.include_router(scenario_runs.router)
    app.include_router(fixtures.router)
    app.include_router(exports.router)


def create_app(settings_factory: Callable[[], Settings] = get_settings) -> FastAPI:
    settings = settings_factory()
    app = FastAPI(
        title=settings.app_name,
        docs_url=settings.effective_docs_url,
        openapi_url=settings.effective_openapi_url,
    )
    app.state.settings = settings
    configure_logging(settings)
    register_security_response_middleware(app)
    if settings.backend_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.backend_cors_origins,
            allow_credentials=False,
            allow_methods=BROWSER_CORS_READ_METHODS,
            allow_headers=["Authorization", "Content-Type"],
        )
    register_error_handlers(app)
    register_routes(app)
    return app


def register_security_response_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_response_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.correlation_id = uuid4().hex
        start = time.perf_counter()
        settings = getattr(request.app.state, "settings", None)
        if settings is None:
            settings = get_settings()
        if settings.mutation_api_mode == "read_only" and request.method in MUTATION_METHODS:
            emit_operational_event(
                request,
                event_class="public_mutation_blocked",
                outcome_class="client_error",
                status_code=404,
                duration_ms=_duration_ms(start),
            )
            response = Response(
                status_code=404,
                media_type="application/json",
                content='{"detail":"Not found"}',
            )
            response.headers["X-Request-ID"] = request.state.correlation_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            return response
        try:
            response = await call_next(request)
        except Exception as exc:
            emit_operational_event(
                request,
                event_class="request_exception",
                outcome_class="server_error",
                exception_class=exc.__class__.__name__,
                duration_ms=_duration_ms(start),
            )
            raise
        response.headers["X-Request-ID"] = request.state.correlation_id

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            response.headers["X-Content-Type-Options"] = "nosniff"

        if _requires_no_store(request, response):
            response.headers["Cache-Control"] = "no-store"
        emit_operational_event(
            request,
            event_class="request_completed",
            outcome_class=_outcome_class(response.status_code),
            status_code=response.status_code,
            duration_ms=_duration_ms(start),
            cache_control_class=(
                "no_store" if response.headers.get("Cache-Control") == "no-store" else "default"
            ),
        )
        return response


def _duration_ms(start: float) -> int:
    return max(0, round((time.perf_counter() - start) * 1000))


def _outcome_class(status_code: int) -> str:
    if status_code >= 500:
        return "server_error"
    if status_code >= 400:
        return "client_error"
    return "success"


def _requires_no_store(request: Request, response: Response) -> bool:
    path = request.url.path
    if (request.method, path) in NO_STORE_EXACT_ROUTES:
        return True
    if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in NO_STORE_PREFIXES):
        return True
    return (
        request.method in MUTATION_METHODS
        and response.status_code in SECURITY_SENSITIVE_ERROR_STATUSES
    )


app = create_app()
