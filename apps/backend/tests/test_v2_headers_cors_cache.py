import pytest
from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient

from app.core.config import REPO_ROOT, Settings
from app.main import create_app


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_json_nosniff(response) -> None:
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["x-content-type-options"] == "nosniff"


def assert_no_store(response) -> None:
    assert response.headers["Cache-Control"] == "no-store"


def test_cors_is_disabled_by_default_and_local_origins_are_explicitly_configured() -> None:
    default_origins = Settings.model_fields["backend_cors_origins"].get_default(
        call_default_factory=True
    )
    assert default_origins == []

    default_client = TestClient(create_app(lambda: Settings(backend_cors_origins=[])))
    denied = default_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in denied.headers
    assert denied.headers.get("access-control-allow-credentials") != "true"

    local_origins = ["http://localhost:3000", "http://localhost:5173"]
    configured_client = TestClient(
        create_app(lambda: Settings(backend_cors_origins=local_origins))
    )
    allowed = configured_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers.get("access-control-allow-credentials") != "true"


@pytest.mark.parametrize("mutation_method", ["DELETE", "PATCH", "POST", "PUT"])
def test_configured_local_cors_rejects_browser_mutation_preflights(
    mutation_method: str,
) -> None:
    client = TestClient(
        create_app(lambda: Settings(backend_cors_origins=["http://localhost:3000"]))
    )

    allowed_read = client.options(
        "/timelines/public",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied_mutation = client.options(
        "/agents/signup",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": mutation_method,
        },
    )

    assert allowed_read.status_code == 200
    assert allowed_read.headers["access-control-allow-origin"] == "http://localhost:3000"
    allowed_methods = allowed_read.headers["access-control-allow-methods"]
    assert "GET" in allowed_methods
    assert denied_mutation.status_code == 400
    assert "access-control-allow-origin" in denied_mutation.headers
    assert mutation_method not in denied_mutation.headers["access-control-allow-methods"]


def test_local_dev_files_use_explicit_cors_origins_without_wildcards() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173" in env_example
    assert (
        "BACKEND_CORS_ORIGINS: "
        "${BACKEND_CORS_ORIGINS:-http://localhost:3000,http://localhost:5173}"
    ) in compose

    cors_lines = [
        line for text in (env_example, compose) for line in text.splitlines() if "CORS" in line
    ]
    assert cors_lines
    assert all("*" not in line for line in cors_lines)
    assert "allow_credentials=False" in (
        (REPO_ROOT / "apps" / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("get", "/health", {}),
        ("get", "/timelines/public", {}),
        ("get", "/timelines/public?unexpected_filter=wide", {}),
    ],
)
def test_browser_json_responses_include_json_content_type_and_nosniff(
    client: TestClient,
    seeded_world: dict,
    method: str,
    path: str,
    kwargs: dict,
) -> None:
    del seeded_world

    response = getattr(client, method)(path, **kwargs)

    assert_json_nosniff(response)


def test_no_store_on_signup_home_harness_validation_alias_and_export_routes(
    client: TestClient, seeded_world: dict, harness_headers: dict[str, str]
) -> None:
    del seeded_world

    signup = client.post(
        "/agents/signup",
        json={
            "handle": "budget_civic_bot",
            "display_name": "Budget Civic Bot",
            "bio": "Fictional under-$10k inspection notes.",
        },
    )
    home = client.get("/timelines/home", headers=auth_headers("agent_alex_fixture"))
    fixture_seed = client.post("/fixtures/seed", headers=harness_headers)
    validation_list = client.get("/validation-runs", headers=harness_headers)
    validation_create = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={
            "scenario_id": "RT-V2-CACHE",
            "objective": "Synthetic cache posture check.",
        },
    )
    run_id = validation_create.json()["id"]
    validation_event = client.post(
        f"/validation-runs/{run_id}/events",
        headers=harness_headers,
        json={
            "event_type": "cache_check",
            "redacted_summary": "Synthetic validation cache event.",
        },
    )
    validation_finding = client.post(
        f"/validation-runs/{run_id}/findings",
        headers=harness_headers,
        json={
            "severity": "low",
            "redacted_evidence_summary": "Synthetic validation cache finding.",
        },
    )
    scenario_alias = client.get("/scenario-runs", headers=harness_headers)
    findings = client.get("/findings", headers=harness_headers)
    export = client.post("/exports/public-evidence", headers=harness_headers)

    responses = [
        signup,
        home,
        fixture_seed,
        validation_list,
        validation_create,
        validation_event,
        validation_finding,
        scenario_alias,
        findings,
        export,
    ]
    assert [response.status_code for response in responses] == [
        201,
        200,
        200,
        200,
        201,
        201,
        201,
        200,
        200,
        200,
    ]
    for response in responses:
        assert_no_store(response)
        assert_json_nosniff(response)


def test_security_sensitive_mutation_errors_are_no_store_json_and_redacted(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    bearer_marker = "bearer_value_must_not_appear_placeholder"
    token_hash_marker = "token_hash_marker_placeholder"
    raw_body_marker = "raw_body_marker_placeholder"

    missing_auth = client.post("/posts", json={"text": "Synthetic missing auth note."})
    invalid_auth = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {bearer_marker}"},
        json={"text": "Synthetic invalid auth note."},
    )
    wrong_authority = client.post(
        "/fixtures/reset", headers=auth_headers("agent_alex_fixture")
    )
    invalid_body = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic protected-field rejection note.",
            "token_hash": token_hash_marker,
            "raw_body": raw_body_marker,
        },
    )

    for response, status_code in [
        (missing_auth, 401),
        (invalid_auth, 401),
        (wrong_authority, 403),
        (invalid_body, 422),
    ]:
        assert response.status_code == status_code
        assert_no_store(response)
        assert_json_nosniff(response)
        response_text = response.text
        assert bearer_marker not in response_text
        assert token_hash_marker not in response_text
        assert raw_body_marker not in response_text
        assert "Authorization" not in response_text
