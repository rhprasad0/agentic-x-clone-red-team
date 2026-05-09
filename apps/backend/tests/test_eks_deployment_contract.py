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


def test_runner_cronjob_is_private_suspended_and_bounded() -> None:
    service_account = docs_by_kind("deploy/k8s/base/runner-cronjob.yaml", "ServiceAccount")[0]
    cronjob = docs_by_kind("deploy/k8s/base/runner-cronjob.yaml", "CronJob")[0]
    pod_spec = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]
    env = {item["name"]: str(item["value"]) for item in container["env"]}

    assert service_account["automountServiceAccountToken"] is False
    assert cronjob["spec"]["suspend"] is True
    assert cronjob["spec"]["concurrencyPolicy"] == "Forbid"
    assert cronjob["spec"]["jobTemplate"]["spec"]["activeDeadlineSeconds"] == 900
    assert pod_spec["serviceAccountName"] == "xclone-synthetic-runner"
    assert pod_spec["automountServiceAccountToken"] is False
    assert env["AI_ACTIVITY_API_BASE_URL"] == "http://xclone-backend-internal.xclone-demo.svc.cluster.local:8000"
    assert env["AI_ACTIVITY_AGENT_COUNT"] == "4"
    assert container["securityContext"]["readOnlyRootFilesystem"] is True


def test_network_policy_only_allows_runner_to_internal_mutation_backend() -> None:
    policies = {
        policy["metadata"]["name"]: policy
        for policy in docs_by_kind("deploy/k8s/base/network-policies.yaml", "NetworkPolicy")
    }

    assert "default-deny" in policies
    assert policies["default-deny"]["spec"]["podSelector"] == {}
    assert set(policies["default-deny"]["spec"]["policyTypes"]) == {"Ingress", "Egress"}

    internal_policy = policies["allow-runner-to-internal-backend"]
    internal_selector = internal_policy["spec"]["podSelector"]["matchLabels"]
    assert internal_selector["app.kubernetes.io/component"] == "backend-internal"
    ingress_from = internal_policy["spec"]["ingress"][0]["from"][0]["podSelector"]["matchLabels"]
    assert ingress_from["app.kubernetes.io/component"] == "synthetic-runner"

    runner_policy = policies["allow-runner-egress"]
    runner_selector = runner_policy["spec"]["podSelector"]["matchLabels"]
    assert runner_selector["app.kubernetes.io/component"] == "synthetic-runner"
    first_egress_to = runner_policy["spec"]["egress"][0]["to"][0]["podSelector"]["matchLabels"]
    assert first_egress_to["app.kubernetes.io/component"] == "backend-internal"


def test_kustomization_lists_private_runner_boundary_resources() -> None:
    kustomization = load_docs("deploy/k8s/base/kustomization.yaml")[0]

    assert kustomization["namespace"] == "xclone-demo"
    assert kustomization["resources"] == [
        "namespace.yaml",
        "secrets.example.yaml",
        "backend-public.yaml",
        "backend-internal.yaml",
        "runner-cronjob.yaml",
        "network-policies.yaml",
    ]
