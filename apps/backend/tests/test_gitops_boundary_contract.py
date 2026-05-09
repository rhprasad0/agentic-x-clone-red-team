from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_docs(relative_path: str) -> list[dict]:
    docs = list(yaml.safe_load_all((REPO_ROOT / relative_path).read_text(encoding="utf-8")))
    return [doc for doc in docs if doc]


def by_name(docs: list[dict], kind: str, name: str) -> dict:
    return next(doc for doc in docs if doc.get("kind") == kind and doc["metadata"]["name"] == name)


def test_gitops_service_accounts_keep_tokens_narrow() -> None:
    docs = load_docs("deploy/gitops/apps/base/serviceaccounts.yaml")

    assert by_name(docs, "ServiceAccount", "default")["automountServiceAccountToken"] is False
    frontend = by_name(docs, "ServiceAccount", "xclone-frontend")
    assert frontend["automountServiceAccountToken"] is False

    backend = by_name(docs, "ServiceAccount", "xclone-backend")
    assert backend["automountServiceAccountToken"] is False
    assert "annotations" not in backend["metadata"]


def test_gitops_network_policies_are_default_deny_with_narrow_runtime_allows() -> None:
    policies = load_docs("deploy/gitops/apps/base/networkpolicies.yaml")
    names = {policy["metadata"]["name"] for policy in policies}

    assert "xclone-default-deny" in names
    assert "allow-vpc-to-frontend" in names
    assert "allow-vpc-to-public-read-api" in names
    assert "allow-runtime-egress" in names

    serialized = yaml.safe_dump_all(policies)
    assert "namespaceSelector: {}" not in serialized
    assert "10.42.0.0/16" in serialized
    assert "port: 5432" in serialized
    assert "port: 443" in serialized


def test_alb_ingress_group_is_class_param_controlled() -> None:
    controller_path = (
        REPO_ROOT / "deploy/gitops/platform/controllers/aws-load-balancer-controller.yaml"
    )
    controller = yaml.safe_load_all(controller_path.read_text(encoding="utf-8"))
    release = next(doc for doc in controller if doc and doc.get("kind") == "HelmRelease")
    values = release["spec"]["values"]

    assert values["ingressClassParams"]["name"] == "alb"
    assert values["ingressClassParams"]["spec"]["group"]["name"] == "xclone-public"
    assert values["ingressClassParams"]["spec"]["namespaceSelector"]["matchLabels"] == {
        "kubernetes.io/metadata.name": "xclone"
    }
    assert values["disableIngressGroupNameAnnotation"] is True

    ingress = (REPO_ROOT / "deploy/gitops/apps/base/ingress.yaml").read_text(encoding="utf-8")
    assert "alb.ingress.kubernetes.io/group.name" not in ingress
    assert "conditions.xclone-backend-public-read" in ingress
