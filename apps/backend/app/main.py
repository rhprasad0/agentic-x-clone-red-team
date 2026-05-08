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
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.correlation_id

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            response.headers["X-Content-Type-Options"] = "nosniff"

        if _requires_no_store(request, response):
            response.headers["Cache-Control"] = "no-store"
        return response


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
