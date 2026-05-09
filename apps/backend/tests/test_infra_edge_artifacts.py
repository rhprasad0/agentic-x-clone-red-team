from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_edge_runbook_documents_dns_tls_and_public_api_boundaries() -> None:
    runbook = (REPO_ROOT / "docs/infra/aws-edge-dns-runbook.md").read_text()

    assert "xclone.ryans-lab.click" in runbook
    assert "api.xclone.ryans-lab.click" in runbook
    assert "ENABLE_API_DOCS=false" in runbook
    assert "terraform output -raw acm_certificate_arn" in runbook
    assert "aws route53 list-resource-record-sets" in runbook
    assert "curl -fsS https://api.xclone.ryans-lab.click/health" in runbook
    assert "ExternalDNS remains a later/narrow exception" in runbook


def test_alb_ingress_keeps_frontend_and_api_hosts_explicit() -> None:
    ingress = (REPO_ROOT / "infra/k8s/xclone/alb-ingress.yaml").read_text()

    assert "ingressClassName: alb" in ingress
    assert "alb.ingress.kubernetes.io/group.name" not in ingress
    assert "alb.ingress.kubernetes.io/conditions.xclone-backend-public-read" in ingress
    assert "xclone-backend-public-read" in ingress
    assert "alb.ingress.kubernetes.io/certificate-arn" in ingress
    assert "host: xclone.ryans-lab.click" in ingress
    assert "host: api.xclone.ryans-lab.click" in ingress
    assert "healthcheck-path: /health" in ingress


def test_terraform_edge_layer_has_acm_route53_and_controller_contracts() -> None:
    terraform_dir = REPO_ROOT / "infra/terraform/aws"
    terraform_text = "\n".join(path.read_text() for path in terraform_dir.glob("*.tf"))

    assert "aws_acm_certificate" in terraform_text
    assert "aws_acm_certificate_validation" in terraform_text
    assert "aws_route53_record" in terraform_text
    assert "helm_release" in terraform_text
    assert "aws-load-balancer-controller" in terraform_text
    assert "disableIngressGroupNameAnnotation" in terraform_text
    assert "ingressClassParams.spec.namespaceSelector.matchLabels.kubernetes" in terraform_text
    assert "metadata\\\\.name" in terraform_text
    assert "xclone-public" in terraform_text
    assert "alb_dns_name" in terraform_text
    assert (terraform_dir / "iam/aws-load-balancer-controller-policy.json").exists()
