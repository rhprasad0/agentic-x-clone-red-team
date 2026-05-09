# Final validation review receipt

Date: 2026-05-09
Branch: `kanban/t_2c4f360e`
Scope: integration review for the temporary x-clone EKS/GitOps/GHCR/RDS/edge demo artifacts.

## What this branch integrates

This branch merges the reviewable outputs from the implementation cards into one public-safe review branch:

- AWS demo operations runbook and teardown/receipt scripts.
- GHCR image publishing workflow for backend, frontend, and runner images.
- Flux-compatible GitOps layout for the demo cluster/app split.
- Private single-AZ RDS Terraform slice and Kubernetes migration/secret-reference manifests.
- EKS Terraform baseline receipt and IaC.
- AWS edge/DNS/ALB controller Terraform plus ingress/service-contract artifacts.
- Public mutation-protection controls for the EKS demo runner path.

## Source-consult ledger

- Graphiti group `x-clone`: confirmed supply-chain-gate expectations, prior public-safety results, and EKS/GHCR/RDS/edge decisions.
- Honcho: confirmed Ryan's project preferences for public-safe, credible, direct execution and the x-clone repo location/context.
- AWS documentation search: checked EKS assurance/best-practices and ALB controller troubleshooting guidance for validation framing.
- Context7: checked Terraform AWS provider docs for ACM/Route53 validation patterns.
- Current repo files and parent kanban handoffs: used as the source of truth for branch integration and validation targets.

## Validation performed

Terraform:

- `terraform fmt -check`, `terraform init -backend=false -input=false`, and `terraform validate` passed for:
  - `infra/terraform/eks-demo`
  - `infra/terraform/demo-rds`
  - `infra/terraform/aws`
- Live-state-backed `terraform plan -detailed-exitcode` returned `0` (no changes) for:
  - `infra/terraform/eks-demo`
  - `infra/terraform/aws`
- `infra/terraform/demo-rds` validation passed, but a live plan was intentionally not run because this standalone slice still requires local-only values: `vpc_id`, `private_subnet_ids`, and `eks_cluster_security_group_id`.

AWS live checks:

- EKS cluster `xclone-demo` is `ACTIVE` on Kubernetes 1.33.
- Managed node group is `ACTIVE` with desired size 2.
- EKS add-ons are `ACTIVE`: CoreDNS, VPC CNI, kube-proxy, and EKS Pod Identity Agent.
- Demo RDS PostgreSQL instance is `available`, private, and single-AZ.
- Demo ALB is active and internet-facing for the public read surface.
- `xclone.ryans-lab.click` and `api.xclone.ryans-lab.click` resolve; both return HTTP 503 as expected until app workloads/endpoints are deployed.

Kubernetes/GitOps/manifests:

- YAML multi-document parse passed for 39 files / 73 resources across `deploy`, `infra/k8s`, and `clusters`.
- Kustomization resource and patch references resolved.
- GitHub Actions workflow YAML parsed successfully.
- Dockerized `actionlint` passed for `.github/workflows/ci.yml` and `.github/workflows/publish-ghcr-images.yml`.

Application and supply chain:

- Backend targeted infra/runtime tests: 21 passed.
- Full backend test suite: 236 passed, 1 warning.
- Backend `ruff`, `mypy`, and `pip-audit --local` passed.
- Frontend `npm ci`, typecheck, lint, tests, build, and high-severity audit passed; 22 frontend tests passed.
- Docker builds passed for backend, frontend, and runner validation images.
- Dockerized Trivy HIGH/CRITICAL vulnerability scans passed for backend, frontend, and runner validation images.
- Dockerized Trivy CycloneDX SBOM generation succeeded for backend, frontend, and runner local receipts; generated SBOMs were email-redacted, JSON-reformatted, and passed the public-safety scanner.

Public safety / repo hygiene:

- `python3 scripts/public_safety_scan.py .` passed.
- Public-safety scan passed over generated local SBOM receipts.
- `git diff --check` passed.
- No Terraform state, tfvars, raw receipts, SBOM JSON, node modules, or local logs are intended for commit.

## Applied vs prepared

Applied / live:

- EKS baseline, node group, add-ons, private RDS inside the EKS baseline, ALB controller/edge layer, ACM/DNS aliases, and public ALB are live from the parent apply cards.
- Final no-op Terraform plans were verified for the applied EKS baseline and edge/DNS layers using local ignored state/variable files.

Prepared / reviewable only:

- The standalone `infra/terraform/demo-rds` slice remains prepared and validated, but not live-planned from this branch because its required VPC/subnet/EKS security-group values are deliberately local-only.
- GitOps manifests, public GHCR workflow, and runner/mutation-protection artifacts are reviewable in git; actual Flux bootstrap/image automation write-back and post-first-publish GHCR public visibility toggle remain operator steps.
- App workloads are not yet deployed behind the ALB; the public hostnames currently returning 503 is expected at this stage.

## Remaining operator steps

1. Review and merge the implementation PRs or this integration branch in the intended order.
2. After first GHCR publish from `main`, make the backend/frontend/runner GHCR packages public and smoke-check anonymous pulls.
3. Deploy or reconcile the app workloads through Flux/GitOps after image tags/digests are ready.
4. For the standalone demo-RDS slice, provide local-only `vpc_id`, `private_subnet_ids`, and `eks_cluster_security_group_id` before running a live plan/apply.
5. Re-run the receipt collection script after app workloads are healthy so public-facing HTTP probes show application responses rather than expected ALB 503s.

## Teardown instructions

Use the public-safe runbook `docs/aws-demo-operations-runbook.md` and scripts:

1. Collect final receipts first with `scripts/aws_demo_collect_receipts.sh`.
2. Suspend/delete the private runner CronJob before teardown.
3. Remove or wait for Kubernetes Ingress/ALB cleanup as needed.
4. Run `scripts/aws_demo_teardown.sh` with explicit destroy approval and the correct local Terraform directory/state.
5. Run `scripts/aws_demo_post_destroy_verify.sh` to confirm no intended demo EKS, ALB, NAT Gateway, RDS, volumes, or unintended snapshots remain.

Keep raw local receipts, Terraform state, tfvars, plans, and AWS identifiers out of commits.
