import re
from typing import Any

from fastapi.routing import APIRoute

from app.core.config import Settings
from app.main import create_app

EXPECTED_ROUTE_POSTURE = {
    ("GET", "/health"): ("public", "health", "health"),
    ("POST", "/agents/signup"): ("public", "agent_signup", "agent"),
    ("GET", "/agents"): ("public", "agent_read", "agent"),
    ("GET", "/agents/{handle}"): ("public", "agent_read", "agent"),
    ("GET", "/agents/{handle}/posts"): ("public", "agent_read", "post"),
    ("GET", "/agents/{handle}/replies"): ("public", "agent_read", "post"),
    ("GET", "/agents/{handle}/likes"): ("public", "agent_read", "relationship"),
    ("GET", "/agents/{handle}/reposts"): ("public", "agent_read", "relationship"),
    ("GET", "/timeline"): ("public", "timeline_read", "timeline"),
    ("GET", "/timelines/public"): ("public", "timeline_read", "timeline"),
    ("GET", "/timelines/home"): ("synthetic_agent", "timeline_read", "timeline"),
    ("GET", "/posts/{post_id}/thread"): ("public", "post_read", "post"),
    ("POST", "/posts"): ("synthetic_agent", "social_mutation", "post"),
    ("POST", "/posts/{post_id}/like"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("DELETE", "/posts/{post_id}/like"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("POST", "/posts/{post_id}/repost"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("DELETE", "/posts/{post_id}/repost"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("POST", "/agents/{handle}/follow"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("DELETE", "/agents/{handle}/follow"): (
        "synthetic_agent",
        "social_mutation",
        "relationship",
    ),
    ("POST", "/fixtures/seed"): ("harness", "fixture", "fixture"),
    ("POST", "/fixtures/reset"): ("harness", "fixture", "fixture"),
    ("GET", "/validation-runs"): ("harness", "validation_artifact", "validation_run"),
    ("POST", "/validation-runs"): ("harness", "validation_artifact", "validation_run"),
    ("GET", "/validation-runs/{run_id}"): (
        "harness",
        "validation_artifact",
        "validation_run",
    ),
    ("GET", "/validation-runs/{run_id}/events"): (
        "harness",
        "validation_artifact",
        "validation_event",
    ),
    ("POST", "/validation-runs/{run_id}/events"): (
        "harness",
        "validation_artifact",
        "validation_event",
    ),
    ("GET", "/validation-runs/{run_id}/findings"): (
        "harness",
        "validation_artifact",
        "finding",
    ),
    ("POST", "/validation-runs/{run_id}/findings"): (
        "harness",
        "validation_artifact",
        "finding",
    ),
    ("GET", "/findings"): ("harness", "validation_artifact", "finding"),
    ("GET", "/findings/{finding_id}"): (
        "harness",
        "validation_artifact",
        "finding",
    ),
    ("GET", "/scenario-runs"): (
        "harness",
        "validation_artifact",
        "validation_run",
    ),
    ("POST", "/scenario-runs"): (
        "harness",
        "validation_artifact",
        "validation_run",
    ),
    ("GET", "/scenario-runs/{run_id}"): (
        "harness",
        "validation_artifact",
        "validation_run",
    ),
    ("GET", "/scenario-runs/{run_id}/events"): (
        "harness",
        "validation_artifact",
        "validation_event",
    ),
    ("POST", "/scenario-runs/{run_id}/events"): (
        "harness",
        "validation_artifact",
        "validation_event",
    ),
    ("GET", "/scenario-runs/{run_id}/findings"): (
        "harness",
        "validation_artifact",
        "finding",
    ),
    ("POST", "/scenario-runs/{run_id}/findings"): (
        "harness",
        "validation_artifact",
        "finding",
    ),
    ("POST", "/exports/public-evidence"): (
        "harness",
        "export",
        "public_evidence_export",
    ),
}

EXPECTED_ALIASES = {
    ("GET", "/timeline"): "/timelines/public",
    ("GET", "/scenario-runs"): "/validation-runs",
    ("POST", "/scenario-runs"): "/validation-runs",
    ("GET", "/scenario-runs/{run_id}"): "/validation-runs/{run_id}",
    ("GET", "/scenario-runs/{run_id}/events"): "/validation-runs/{run_id}/events",
    ("POST", "/scenario-runs/{run_id}/events"): "/validation-runs/{run_id}/events",
    ("GET", "/scenario-runs/{run_id}/findings"): "/validation-runs/{run_id}/findings",
    ("POST", "/scenario-runs/{run_id}/findings"): "/validation-runs/{run_id}/findings",
}


def route_inventory() -> dict[tuple[str, str], dict[str, Any]]:
    inventory: dict[tuple[str, str], dict[str, Any]] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            inventory[(method, route.path)] = {
                "auth_class": getattr(route.endpoint, "v2_auth_class", None),
                "route_class": getattr(route.endpoint, "v2_route_class", None),
                "target_object_class": getattr(
                    route.endpoint, "v2_target_object_class", None
                ),
                "alias_for": getattr(route.endpoint, "v2_alias_for", None),
                "include_in_schema": route.include_in_schema,
            }
    return inventory


def test_runtime_route_inventory_lists_known_v2_and_compatibility_routes() -> None:
    inventory = route_inventory()

    assert set(inventory) == set(EXPECTED_ROUTE_POSTURE)
    for key, (
        expected_auth_class,
        expected_route_class,
        expected_target_object_class,
    ) in EXPECTED_ROUTE_POSTURE.items():
        assert inventory[key]["auth_class"] == expected_auth_class
        assert inventory[key]["route_class"] == expected_route_class
        assert inventory[key]["target_object_class"] == expected_target_object_class


def test_compatibility_aliases_are_explicit_and_excluded_from_openapi_schema() -> None:
    inventory = route_inventory()

    for key, canonical_path in EXPECTED_ALIASES.items():
        assert inventory[key]["alias_for"] == canonical_path
        if key != ("GET", "/timeline"):
            assert inventory[key]["include_in_schema"] is False

    for key in set(inventory) - set(EXPECTED_ALIASES):
        assert inventory[key]["alias_for"] is None


def test_docs_and_debug_posture_has_no_hidden_public_admin_routes() -> None:
    local_paths = {route.path for route in create_app().routes}
    assert "/docs" in local_paths
    assert "/openapi.json" in local_paths

    docs_disabled_paths = {
        route.path
        for route in create_app(lambda: Settings(enable_api_docs=False)).routes
    }
    assert "/docs" not in docs_disabled_paths
    assert "/openapi.json" not in docs_disabled_paths

    exposed_api_paths = {
        route.path for route in create_app().routes if isinstance(route, APIRoute)
    }
    hidden_public_debug_paths = {
        path
        for path in exposed_api_paths
        if re.search(r"/(admin|debug|internal|metrics|ops|shell)(?:/|$)", path)
    }
    assert hidden_public_debug_paths == set()
