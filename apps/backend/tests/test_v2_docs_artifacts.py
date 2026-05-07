import json
import re
from pathlib import Path

from test_v2_runtime_route_inventory import EXPECTED_ALIASES, route_inventory

REPO_ROOT = Path(__file__).resolve().parents[3]
API_INVENTORY = REPO_ROOT / "docs" / "api-inventory.md"
OPENAPI_SNAPSHOT = REPO_ROOT / "docs" / "openapi-v2.json"
V2_LOCAL_RUNBOOK = REPO_ROOT / "docs" / "v2-local-runbook.md"
DOCKER_COMPOSE = REPO_ROOT / "docker-compose.yml"
BACKEND_DOCKERFILE = REPO_ROOT / "apps" / "backend" / "Dockerfile"
DOCS_TO_SCAN = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "SPEC.md",
    REPO_ROOT / "docs" / "api-inventory.md",
    REPO_ROOT / "docs" / "architecture.md",
    REPO_ROOT / "docs" / "project-scope.md",
    REPO_ROOT / "SECURITY_REQUIREMENTS.md",
    REPO_ROOT / "THREAT_MODEL.md",
]


def _inventory_rows() -> set[tuple[str, str]]:
    rows: set[tuple[str, str]] = set()
    table_row = re.compile(r"^\| `(?P<method>[A-Z]+)` \| `(?P<path>[^`]+)` \|")
    for line in API_INVENTORY.read_text(encoding="utf-8").splitlines():
        match = table_row.match(line)
        if match:
            rows.add((match.group("method"), match.group("path")))
    return rows


def test_openapi_v2_snapshot_matches_schema_included_runtime_routes() -> None:
    assert OPENAPI_SNAPSHOT.exists()
    snapshot = json.loads(OPENAPI_SNAPSHOT.read_text(encoding="utf-8"))
    snapshot_routes = {
        (method.upper(), path)
        for path, operations in snapshot["paths"].items()
        for method in operations
    }
    runtime_schema_routes = {
        key
        for key, metadata in route_inventory().items()
        if metadata["include_in_schema"] is True
    }

    assert snapshot_routes == runtime_schema_routes


def test_api_inventory_documents_every_runtime_route_and_alias() -> None:
    docs_routes = _inventory_rows()
    runtime_routes = set(route_inventory())

    assert docs_routes == runtime_routes

    inventory_text = API_INVENTORY.read_text(encoding="utf-8")
    for (_method, alias_path), canonical_path in EXPECTED_ALIASES.items():
        assert f"`{alias_path}`" in inventory_text
        assert canonical_path in inventory_text
        assert "compatibility alias" in inventory_text.lower()

    assert "`/users" not in inventory_text
    assert "canonical noun" in inventory_text
    assert "agents" in inventory_text


def test_backend_container_bootstraps_fixture_auth_before_local_smoke_routes() -> None:
    dockerfile_text = BACKEND_DOCKERFILE.read_text(encoding="utf-8")

    assert "seed_used_car_world" in dockerfile_text
    assert "alembic -c alembic.ini upgrade head" in dockerfile_text
    assert "exec uvicorn app.main:app" in dockerfile_text


def test_docker_compose_host_ports_are_env_overridable_for_parallel_smoke() -> None:
    compose_text = DOCKER_COMPOSE.read_text(encoding="utf-8")

    required_port_bindings = [
        '"${POSTGRES_HOST_PORT:-5432}:5432"',
        '"${BACKEND_HOST_PORT:-8000}:8000"',
        '"${FRONTEND_HOST_PORT:-3000}:8080"',
        'BACKEND_CORS_ORIGINS: ${BACKEND_CORS_ORIGINS:-http://localhost:3000,http://localhost:5173}',
    ]
    for binding in required_port_bindings:
        assert binding in compose_text


def test_v2_local_runbook_covers_smoke_and_public_safety_workflow() -> None:
    assert V2_LOCAL_RUNBOOK.exists()
    runbook = V2_LOCAL_RUNBOOK.read_text(encoding="utf-8")

    required_phrases = [
        "local-only V2 smoke",
        "docker compose config",
        "docker compose build",
        "docker compose up -d",
        "alembic -c alembic.ini upgrade head",
        "python3 scripts/reset_fixtures.py",
        "python3 scripts/seed_fixtures.py",
        "curl -fsS http://localhost:8000/health",
        "curl -fsS http://localhost:8000/timelines/public",
        "curl -fsS http://localhost:8000/agents",
        "curl -fsS http://localhost:8000/posts/",
        "POST /agents/signup",
        "display-once token must be redacted",
        "POST /exports/public-evidence",
        "npm audit --omit=dev --audit-level=high",
        "python3 scripts/public_safety_scan.py .",
        "do not publish hidden scenario catalogs",
    ]
    for phrase in required_phrases:
        assert phrase in runbook

    forbidden_phrases = [
        "production-ready",
        "real users",
        "real platform data",
        "comprehensive security assessment",
        "token: ",
        "bearer ey",
    ]
    for phrase in forbidden_phrases:
        assert phrase.lower() not in runbook.lower()


def test_public_docs_keep_v2_claims_bounded_and_billboard_safe() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS_TO_SCAN)
    forbidden_claims = [
        "production-ready",
        "completed hardening",
        "comprehensive security",
        "real users",
        "real platform data",
        "affiliated with X",
        "affiliated with Twitter",
        "affiliated with xAI",
    ]

    for phrase in forbidden_claims:
        assert phrase.lower() not in combined.lower()

    required_boundaries = [
        "synthetic",
        "local-first",
        "not a production deployment claim",
        "read-only observability",
        "validation language stays at product/route/control/artifact/data-class level",
    ]
    for phrase in required_boundaries:
        assert phrase.lower() in combined.lower()
