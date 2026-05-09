# AWS Demo Operations Runbook

This runbook makes the short-lived EKS demo boring to operate and easy to kill. That is the point. The public portfolio artifact should show a production-shaped deployment without accidentally becoming a tiny money furnace with a login page.

The repo does not commit live AWS identifiers, account IDs, ARNs, raw logs, private paths, bearer values, or screenshots. The scripts below write receipts under `.hermes/tmp/aws-demo-receipts/`, which is ignored by git. Publish only reviewed, redacted excerpts.

## Grounded decisions

- Scope: temporary small demo for a handful of visitors.
- Cost mode: single-NAT demo mode, minimal node group, small RDS, short log retention.
- Surface: public frontend and public read API only; mutation/harness/admin paths should be denied at the public edge before they reach the backend. The AI activity runner is on-prem only, not an EKS CronJob.
- Ownership: Terraform owns AWS primitives; Flux/Kubernetes owns in-cluster desired state.
- Teardown: destroy from Terraform, but delete/suspend Kubernetes resources first so the AWS Load Balancer Controller can release ALBs cleanly.

## Required tags

Every Terraform-managed AWS resource that supports tags should carry these cost/TTL tags:

```text
Project=x-clone
Environment=demo
Owner=portfolio-demo
ManagedBy=terraform
PublicEvidence=false
ttl-hours=48
expires-at=YYYY-MM-DDTHH:MM:SSZ
```

Terraform should prefer provider-level `default_tags` and add resource-specific tags only when needed. The AWS provider merges provider defaults into resource `tags_all`; remember that Auto Scaling resources may need explicit tag propagation.

Suggested Terraform variable shape:

```hcl
variable "ttl_hours" {
  type        = number
  default     = 48
  description = "Maximum intended lifetime for the temporary demo."

  validation {
    condition     = var.ttl_hours > 0 && var.ttl_hours <= 168
    error_message = "ttl_hours must be between 1 and 168 for the temporary demo."
  }
}

locals {
  common_tags = {
    Project        = "x-clone"
    Environment    = "demo"
    Owner          = "portfolio-demo"
    ManagedBy      = "terraform"
    PublicEvidence = "false"
    ttl-hours      = tostring(var.ttl_hours)
    expires-at     = var.expires_at
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}
```

Use the same tag values in Kubernetes `Ingress`/Service annotations for ALB tags where the load balancer is created by the AWS Load Balancer Controller.

## Cost controls

Baseline controls for the small public demo:

- One EKS managed node group sized for the demo, not a fleet.
- t3.micro/t3.small-class nodes where credible for the app; scale up only with evidence.
- Single-AZ/small RDS for demo economics; document the lower-HA tradeoff.
- One NAT gateway in single-NAT mode; avoid per-AZ NAT sprawl.
- Public GHCR images to avoid pull-secret complexity.
- ECR lifecycle guidance if ECR is later introduced: expire untagged images aggressively and keep only a bounded count or age window for SHA-tagged demo images.
- CloudWatch log retention set explicitly; do not rely on indefinite retention.
- No always-on Container Insights unless a later task explicitly decides the extra cost is worth the evidence.

## Log retention and evidence policy

Recommended minimum observability for the demo:

- EKS control-plane logs: enable `api`, `audit`, and `authenticator` for deployment/security receipts; keep retention short.
- Backend application logs: structured JSON with event class, route class, status/outcome class, request ID, and duration bucket.
- Frontend diagnostics: class-level read failures and request IDs only.
- Runner logs: class-level events only, written to ignored local receipt paths.
- ALB access logs: optional but useful for a public-health receipt; store in S3 with lifecycle expiration.

Do not commit raw logs. Public excerpts should show only class-level health and control evidence, not client IPs, account IDs, ARNs, tokens, paths, or private environment output.

## Smoke checks before calling the demo healthy

Set placeholder-safe environment variables locally:

```bash
export AWS_REGION=us-east-1
export CLUSTER_NAME=xclone-demo
export NAMESPACE=xclone
export FRONTEND_URL=https://xclone.example.com
export API_URL=https://api.xclone.example.com
```

Run public read-path checks:

```bash
curl -fsSI "$FRONTEND_URL"
curl -fsS "$API_URL/health"
curl -fsS "$API_URL/timelines/public?limit=3"
curl -fsSI "$API_URL/docs"
curl -fsSI "$API_URL/openapi.json"
```

Expected posture:

- Frontend and `/health` answer.
- Public timeline returns synthetic public data.
- `/docs` and `/openapi.json` are absent or denied on the public API.
- Public `POST`, `PUT`, `PATCH`, `DELETE`, signup, harness, export, admin, and debug routes are denied externally. For the current ALB-constrained public demo, the expected outside-cluster denial origin is an edge/ALB fixed response, not backend JSON auth.

Collect a local private receipt:

```bash
./scripts/aws_demo_collect_receipts.sh
```

The receipt lands in `.hermes/tmp/aws-demo-receipts/observability-receipts.md` and is intentionally not a committed artifact.

## Teardown runbook

Teardown should be rehearsed before the demo and run immediately when the demo is no longer needed. Tiny cloud bonfires still produce real bills.

1. Collect final health/evidence receipts:

   ```bash
   ./scripts/aws_demo_collect_receipts.sh
   ```

2. Run a dry-run destroy plan:

   ```bash
   ./scripts/aws_demo_teardown.sh
   ```

3. Review the redacted Terraform destroy plan under `.hermes/tmp/aws-demo-receipts/`.

4. Destroy only after review:

   ```bash
   DESTROY_APPROVAL=destroy-xclone-demo ./scripts/aws_demo_teardown.sh
   ```

5. Verify cleanup:

   ```bash
   ./scripts/aws_demo_post_destroy_verify.sh
   ```

The teardown script deletes Ingress objects to give the AWS Load Balancer Controller a chance to release ALBs, runs `terraform plan -destroy`, and only applies when `DESTROY_APPROVAL=destroy-xclone-demo` is explicitly set.

## Post-destroy verification checklist

The post-destroy verification receipt should show no remaining demo resources for:

- EKS cluster by demo cluster name.
- Tagged ALB/NLB resources.
- Tagged NAT gateways.
- Tagged RDS DB instances.
- Tagged unattached EBS volumes.
- Tagged snapshots that are not intentionally retained.
- Demo CloudWatch log groups beyond the intentionally short retention window.
- ACM/Route53 validation leftovers that Terraform did not own or remove.

If anything remains, either re-run Terraform destroy after the Kubernetes/ALB cleanup delay or remove the specific leftover through a documented follow-up command. Do not mark teardown complete while cost-bearing resources remain.

## Receipt publishing rule

Receipts under `.hermes/tmp/` are private working evidence. If a public artifact is needed, create a small curated summary under `exports/public-evidence/` that says what was checked and the outcome class. Do not paste raw AWS output. Run:

```bash
python3 scripts/public_safety_scan.py exports/public-evidence
python3 scripts/public_safety_scan.py docs/aws-demo-operations-runbook.md scripts/aws_demo_collect_receipts.sh scripts/aws_demo_teardown.sh scripts/aws_demo_post_destroy_verify.sh
git diff --check
```
