# Final validation review receipt

Date: 2026-05-09
Latest live receipt check: 2026-05-09T17:14:04Z
Branch: `kanban/t_a704532f`
Review base / GitOps source: `main` at `ac1bfda19eb6` (`ci: pin GitOps images to 5482e86 [skip ci]`)
Deployed app image tags: backend `sha-5482e86`, frontend `sha-5482e86`
Scope: public-safe validation receipt for the temporary x-clone EKS/GitOps/GHCR/RDS/edge demo.

## What this receipt covers

This receipt updates the earlier integration review after the live EKS demo moved from prepared infrastructure to a healthy public read deployment:

- EKS baseline, managed node group, add-ons, private RDS, ALB controller, ACM/DNS aliases, and public ALB are live.
- Flux is bootstrapped and owns the in-cluster platform/app state: Kyverno, Secrets Store CSI, policies, and app manifests.
- Terraform continues to own AWS/EKS substrate and the AWS Load Balancer Controller.
- Backend and frontend workloads are reconciled from GitOps and running behind the public HTTPS read surface.
- Public mutation/harness/admin-style routes are denied at the ALB edge; the on-prem AI activity runner remains outside EKS.

## Source-consult ledger

- Current repo files and parent kanban handoffs were used as the source of truth for branch integration and validation targets.
- AWS MCP was used by upstream validation cards for EKS, ALB/listener/target-health, IAM, Secrets Manager, and RDS checks.
- Context7 was used by upstream validation cards for Flux, Kyverno, Secrets Store CSI, Kubernetes service/EndpointSlice behavior, and Cosign/Sigstore readiness questions.
- Graphiti/Honcho project memory was consulted by upstream gate cards for x-clone EKS/GitOps/public-safety context.
- This receipt re-ran fresh repo, Kubernetes, public HTTPS, and ELBv2 target-health checks at 2026-05-09T17:14:04Z.

## Live state summary

Kubernetes and GitOps:

- Current kubectl context points at the x-clone EKS demo cluster; full context ARN/account details are intentionally not recorded.
- Nodes: 3 Ready.
- Deployments: `xclone-backend` and `xclone-frontend` are each 1/1 available.
- Pods: backend and frontend pods are Running/Ready with 0 restarts.
- Images: backend/frontend pods run GHCR images pinned to `sha-5482e86`.
- Services/endpoints: `xclone-backend`, `xclone-backend-public-read`, and `xclone-frontend` have populated endpoints. Legacy `xclone-api` remains empty and is not the active public ingress target.
- Ingresses: `xclone-public-api-read` serves `api.xclone.ryans-lab.click`; `xclone-public-frontend` serves `xclone.ryans-lab.click`; both share the public ALB address.
- Flux Kustomizations: app, platform-controller, and platform-policy Kustomizations are Ready against `main`. The image-automation stub remains not Ready/gated and is not required for the public smoke.
- HelmReleases: Kyverno, Secrets Store CSI driver, and AWS Secrets Store CSI provider are Ready.
- Backend SecretProviderClassPodStatus exists and reports mounted=true for the current backend pod.

AWS / edge:

- One matching public x-clone Application Load Balancer is active and internet-facing.
- Active listener set is HTTPS only on port 443.
- Backend public-read target group has 1 healthy IP target with health check path `/health`.
- Frontend target group has 1 healthy IP target with health check path `/`.
- No ALB 503s were observed in the fresh public HTTPS smoke.

## Public smoke summary

Fresh public HTTPS probes at 2026-05-09T17:14:04Z:

- `https://xclone.ryans-lab.click/` returned HTTP 200 `text/html`.
- `https://api.xclone.ryans-lab.click/health` returned HTTP 200 `application/json`.
- `https://api.xclone.ryans-lab.click/timelines/public?limit=3` returned HTTP 200 `application/json`.
- `https://api.xclone.ryans-lab.click/docs` returned HTTP 404 `text/plain`.
- `https://api.xclone.ryans-lab.click/openapi.json` returned HTTP 404 `text/plain`.

The successful read-path checks replace the earlier expected-503 baseline from the prepared-only phase.

## Public mutation-denial summary

The public boundary card verified 22 outside-cluster mutation/bypass probes. All returned edge/ALB fixed-response HTTP 404s, and public read-state hashes/counts were unchanged before and after the probe set.

Covered classes included:

- signup;
- post create/update/delete variants;
- likes, reposts, follows;
- trailing-slash and encoded-path variants;
- method-override header attempts;
- CORS preflight;
- fixture reset/seed;
- validation-run and public-evidence export paths;
- docs and OpenAPI exposure checks.

Denial origin for the current public external surface is ALB/edge routing, not backend JSON auth. This is intentional for the public demo: mutation traffic should not reach the backend through the public read API listener rules.

## Validation performed across the board

Terraform and AWS substrate:

- Terraform fmt/init/validate passed for the EKS baseline and edge/DNS layers in the upstream integration work.
- Live Terraform plans for applied EKS baseline and edge/DNS layers previously reached no-change state from their local ignored state/variable files.
- EKS cluster, managed node group, EKS add-ons, private RDS, ALB controller, ACM/DNS, and public ALB were verified live in upstream cards.
- RDS ingress was corrected to allow the actual EKS-created workload/node security-group path without adding broad CIDR ingress.

Kubernetes/GitOps/platform:

- Flux controllers are installed and reconciling from `main`.
- Kyverno is Flux-owned for this demo; the signed-image policy is installed in Audit/Ignore mode.
- Secrets Store CSI driver/provider are Ready; backend uses EKS Pod Identity for the runtime secret path.
- AWS Load Balancer Controller remains Terraform-owned and is not duplicated by Flux.
- App rollouts are healthy and public ingress routes point to populated backend-public-read and frontend services.

Application and supply chain:

- Backend and frontend GHCR image refs are pinned to `sha-5482e86` for the live app workloads.
- Earlier validation covered backend tests/lint/type/audit, frontend type/lint/tests/build/audit, Docker builds, Trivy HIGH/CRITICAL scans, SBOM generation/sanitization, and public-safety scans.
- GHCR images are suitable for the current public demo path, but Cosign signing/digest-enforced admission remains a later hardening step.

Public safety / repo hygiene:

- Public artifacts avoid secrets, kubeconfig content, bearer tokens, full account IDs, full ARNs, raw private logs, Terraform state, tfvars, and raw receipt dumps.
- Targeted public-safety scan and `git diff --check` were rerun after this receipt update.

## Deviations and caveats

- The checked-in plan file named by the board (`.hermes/plans/2026-05-09_131105-complete-eks-demo-deployment.md`) was not present in this worktree because `.hermes` planning files are not committed; the task was grounded from the kanban body, parent handoffs, current repo files, and the x-clone EKS live-deployment skill reference.
- The app was ultimately reconciled through Flux/GitOps, not a direct `kubectl apply -k` fallback.
- The public ALB currently exposes HTTPS/443 only. Earlier HTTP/80 redirect probes timed out because the listener set is HTTPS-only; treat HTTP redirect behavior as a separate hardening item if required.
- The image automation stub remains gated/not Ready. It is not needed for the current manually pinned `sha-5482e86` public demo deployment.
- The Kyverno signed-image policy is intentionally Audit/Ignore only. Do not switch it to Enforce until backend/frontend images are Cosign-signed by digest and positive/negative admission smokes pass.
- A transient first-mount Pod Identity/CSI warning appeared during app rollout, but final backend pod readiness and SecretProviderClassPodStatus are healthy.
- The public mutation-denial result proves the external public surface denies mutations at the edge. It does not prove app-level mutation denial through a private/internal route because those requests intentionally do not reach the backend from the public ALB.

## Remaining operator steps

1. Keep this demo on a short TTL; it has live EKS, NAT, ALB, and RDS cost-bearing resources.
2. If this deployment stays public beyond the demo window, decide whether to add HTTP/80 redirect coverage or keep HTTPS-only explicit.
3. Before raising signed-image admission from Audit/Ignore to Enforce, add Cosign signing by digest and run positive/negative admission smokes.
4. If image automation is needed, reconcile and validate it separately; the current live demo is pinned manually to `sha-5482e86`.
5. Keep the on-prem AI activity runner out of EKS unless a later card explicitly scopes a controlled runner execution.

## Teardown reminder

Use the public-safe runbook `docs/aws-demo-operations-runbook.md` and scripts:

1. Collect final private receipts first with `scripts/aws_demo_collect_receipts.sh`.
2. Confirm no runner CronJob exists in the app namespace; the runner is on-prem/operator-run only.
3. Delete or suspend Kubernetes Ingress resources first so the AWS Load Balancer Controller can release ALBs cleanly.
4. Run `scripts/aws_demo_teardown.sh` with explicit destroy approval and the correct local Terraform directory/state.
5. Run `scripts/aws_demo_post_destroy_verify.sh` to confirm no intended demo EKS, ALB, NAT Gateway, RDS, volumes, snapshots, or other cost-bearing leftovers remain.

Keep raw local receipts, Terraform state, tfvars, plans, account identifiers, ARNs, kubeconfig content, and secret values out of commits.
