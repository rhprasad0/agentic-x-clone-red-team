from collections.abc import Callable

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import agents, exports, fixtures, posts, scenario_runs, timeline
from app.core.config import Settings, get_settings

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


def register_routes(app: FastAPI) -> None:
    """Register API routes; future route modules should be included here."""

    app.include_router(health_router)
    app.include_router(agents.router)
    app.include_router(timeline.router)
    app.include_router(posts.router)
    app.include_router(scenario_runs.router)
    app.include_router(scenario_runs.finding_router)
    app.include_router(fixtures.router)
    app.include_router(exports.router)


ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: "request_too_large",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "resource_limit",
}


def error_response(status_code: int, message: str, headers: dict[str, str] | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": ERROR_CODES.get(status_code, "error"),
                "message": message,
                "details": None,
            }
        },
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            message = "Unauthorized"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            message = "Forbidden"
        elif isinstance(exc.detail, str):
            message = exc.detail
        else:
            message = "Request failed"
        return error_response(exc.status_code, message, dict(exc.headers or {}))


def create_app(settings_factory: Callable[[], Settings] = get_settings) -> FastAPI:
    settings = settings_factory()
    app = FastAPI(
        title=settings.app_name,
        docs_url=settings.effective_docs_url,
        openapi_url=settings.effective_openapi_url,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    register_routes(app)
    return app


app = create_app()
