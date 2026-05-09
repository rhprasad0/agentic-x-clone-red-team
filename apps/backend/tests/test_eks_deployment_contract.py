import yaml

from app.core.config import REPO_ROOT


def load_docs(relative_path: str) -> list[dict]:
    docs = list(yaml.safe_load_all((REPO_ROOT / relative_path).read_text(encoding="utf-8")))
    return [doc for doc in docs if doc]


def docs_by_kind(relative_path: str, kind: str) -> list[dict]:
    return [doc for doc in load_docs(relative_path) if doc.get("kind") == kind]


def container_env(deployment: dict) -> dict[str, str]:
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    return {item["name"]: str(item["value"]) for item in container.get("env", [])}


def test_public_backend_is_read_only_and_docs_disabled_in_k8s_manifest() -> None:
    deployment = docs_by_kind("deploy/k8s/base/backend-public.yaml", "Deployment")[0]
    service = docs_by_kind("deploy/k8s/base/backend-public.yaml", "Service")[0]
    env = container_env(deployment)

    assert deployment["metadata"]["name"] == "xclone-backend-public"
    assert service["metadata"]["name"] == "xclone-backend-public"
    assert service["spec"]["type"] == "ClusterIP"
    assert env["ENABLE_API_DOCS"] == "false"
    assert env["MUTATION_API_MODE"] == "read_only"
    assert env["BACKEND_CORS_ORIGINS"] == "https://xclone.example.com"


def test_internal_backend_keeps_mutation_mode_off_public_ingress_path() -> None:
    deployment = docs_by_kind("deploy/k8s/base/backend-internal.yaml", "Deployment")[0]
    service = docs_by_kind("deploy/k8s/base/backend-internal.yaml", "Service")[0]
    env = container_env(deployment)

    assert deployment["metadata"]["name"] == "xclone-backend-internal"
    assert service["metadata"]["name"] == "xclone-backend-internal"
    assert service["spec"]["type"] == "ClusterIP"
    assert env["ENABLE_API_DOCS"] == "false"
    assert env["MUTATION_API_MODE"] == "internal"
    assert env["BACKEND_CORS_ORIGINS"] == ""


def test_k8s_base_has_no_runner_cronjob_or_runner_secret() -> None:
    kustomization = load_docs("deploy/k8s/base/kustomization.yaml")[0]
    assert "runner-cronjob.yaml" not in kustomization["resources"]
    assert not (REPO_ROOT / "deploy/k8s/base/runner-cronjob.yaml").exists()

    secrets = docs_by_kind("deploy/k8s/base/secrets.example.yaml", "Secret")
    assert {secret["metadata"]["name"] for secret in secrets} == {"xclone-backend-runtime"}


def test_network_policy_has_no_runner_selectors() -> None:
    policies = docs_by_kind("deploy/k8s/base/network-policies.yaml", "NetworkPolicy")
    policy_names = {policy["metadata"]["name"] for policy in policies}

    assert "default-deny" in policy_names
    assert "allow-public-ingress-to-public-backend" in policy_names
    assert "allow-internal-backend-runtime-egress" in policy_names
    assert all("runner" not in name for name in policy_names)

    serialized = yaml.safe_dump_all(policies)
    assert "synthetic-runner" not in serialized
    assert "xclone-synthetic-runner" not in serialized


def test_kustomization_lists_only_app_backend_boundary_resources() -> None:
    kustomization = load_docs("deploy/k8s/base/kustomization.yaml")[0]

    assert kustomization["namespace"] == "xclone-demo"
    assert kustomization["resources"] == [
        "namespace.yaml",
        "secrets.example.yaml",
        "backend-public.yaml",
        "backend-internal.yaml",
        "network-policies.yaml",
    ]
