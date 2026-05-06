from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Imported for Alembic metadata discovery. Keep these imports at module scope.
from app.models.agent import Agent  # noqa: E402,F401
from app.models.auth_fixture import AuthFixture  # noqa: E402,F401
from app.models.event import Event  # noqa: E402,F401
from app.models.finding import Finding  # noqa: E402,F401
from app.models.post import Post  # noqa: E402,F401
from app.models.scenario_run import ScenarioRun  # noqa: E402,F401
