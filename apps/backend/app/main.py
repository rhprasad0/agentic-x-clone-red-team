from collections.abc import Callable

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    register_routes(app)
    return app


app = create_app()
