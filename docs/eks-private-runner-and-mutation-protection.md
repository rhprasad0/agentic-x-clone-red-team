# EKS public mutation protection receipt

This receipt supersedes the earlier private-runner CronJob design. The current deployment decision keeps the AI activity runner on-prem/operator-run only, outside EKS and outside GHCR deployment automation. The EKS demo now carries only the public/internal backend split, public read-only protections, and Kubernetes reachability boundaries needed for the app workloads.

## Grounding consulted

- Graphiti group `x-clone`: prior `eks-runner-cronjob` and `eks-mutation-api-protection` facts, now narrowed by the on-prem runner decision.
- Honcho continuity: Ryan's small-demo, public-safe, direct-execution preference.
- AWS MCP docs: Amazon EKS VPC CNI NetworkPolicy configuration and standard NetworkPolicy behavior.
- Current repo files: FastAPI route inventory, runtime docs/OpenAPI toggle, CORS read-method policy, AI activity runner CLI, backend/frontend image workflow, and existing public-safe scanner.

## Implemented boundary

The backend supports `MUTATION_API_MODE`:

- `public`: local/default behavior, preserving existing local API-scoped synthetic mutations.
- `internal`: internal backend mode for non-public operator access.
- `read_only`: public backend mode that denies all `POST`, `PUT`, `PATCH`, and `DELETE` before route auth/dependency execution, returns a generic 404 JSON body, sets `Cache-Control: no-store`, and emits class-level denial metadata only.

The legacy Kubernetes base manifests split the backend into two services:

- `xclone-backend-public`: `MUTATION_API_MODE=read_only`, `ENABLE_API_DOCS=false`, explicit browser read CORS, ClusterIP target for the public Ingress/ALB read path.
- `xclone-backend-internal`: `MUTATION_API_MODE=internal`, `ENABLE_API_DOCS=false`, empty CORS, ClusterIP only.

The synthetic runner is **not** an EKS workload anymore:

- no runner `CronJob` is included in the Kubernetes or GitOps bases;
- no runner service account, runner LLM secret, runner ConfigMap, runner image policy, or runner GHCR publish matrix entry is part of the deployment path;
- on-prem runner credentials, bridge access, and runtime state stay outside Kubernetes and outside public receipts.

The NetworkPolicy set includes:

- namespace default deny ingress/egress;
- public-backend ingress rule for cluster ingress/controller paths only;
- backend egress for DNS and database/runtime dependencies.

NetworkPolicy is not treated as an HTTP-method control. The app-level `read_only` mode is the HTTP mutation brake; NetworkPolicy is the pod reachability brake. Belt, suspenders, and a tiny goblin bouncer at the door.

## Validation receipts

Code/tests updated:

- `apps/backend/tests/test_v2_runtime_route_inventory.py` verifies read-only mode blocks mutation methods before route auth and docs/OpenAPI remain absent when disabled.
- `apps/backend/tests/test_eks_deployment_contract.py` verifies the public/internal backend split and asserts runner CronJob/secret/network-policy selectors are absent.

Suggested deployment follow-up before applying to a live cluster:

1. Use the GHCR `backend`/`frontend` image tags produced by CI; do not deploy or publish a runner image for EKS.
2. Replace example backend secret placeholders through External Secrets, AWS Secrets Manager, or an ignored local secret manifest; do not commit real values.
3. Ensure the Terraform-owned EKS VPC CNI add-on has NetworkPolicy enabled before relying on the NetworkPolicy manifests.
4. Keep public Ingress/ALB routing pointed only at `xclone-backend-public`, never at `xclone-backend-internal`.
5. Run public probes against the external API host and record that `/docs`, `/openapi.json`, `POST /agents/signup`, `POST /posts`, social relationship mutation routes, fixture routes, validation mutation routes, and export routes are not exposed on the public host.
