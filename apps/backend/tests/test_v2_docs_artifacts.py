import json
import re
from pathlib import Path

from test_v2_runtime_route_inventory import EXPECTED_ALIASES, route_inventory

REPO_ROOT = Path(__file__).resolve().parents[3]
API_INVENTORY = REPO_ROOT / "docs" / "api-inventory.md"
OPENAPI_SNAPSHOT = REPO_ROOT / "docs" / "openapi-v2.json"
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
