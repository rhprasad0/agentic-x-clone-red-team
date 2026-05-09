# EKS private runner and mutation API protection receipt

This receipt describes the reviewable implementation for keeping the public demo read-only while allowing bounded synthetic-agent mutations only from private/internal Kubernetes paths.

## Grounding consulted

- Graphiti group `x-clone`: `eks-runner-cronjob`, `eks-mutation-api-protection`, public read-only UI facts, and prior mutation-denial facts.
- Honcho continuity: Ryan's latest constraints for a small demo, modest sizing, single-NAT demo mode, public-safety boundaries, and direct execution preference.
- AWS MCP docs: Amazon EKS VPC CNI NetworkPolicy configuration and standard NetworkPolicy behavior.
- Context7 Kubernetes docs: CronJob fields, ServiceAccount usage, and NetworkPolicy default-deny / podSelector patterns.
- Current repo files: FastAPI route inventory, runtime docs/OpenAPI toggle, CORS read-method policy, AI activity runner CLI, backend image, and existing public-safe scanner.

## Implemented boundary

The backend now supports `MUTATION_API_MODE`:

- `public`: local/default behavior, preserving existing local API-scoped synthetic mutations.
- `internal`: internal backend mode for private worker access.
- `read_only`: public backend mode that denies all `POST`, `PUT`, `PATCH`, and `DELETE` before route auth/dependency execution, returns a generic 404 JSON body, sets `Cache-Control: no-store`, and emits class-level denial metadata only.

The Kubernetes base manifests split the backend into two services:

- `xclone-backend-public`: `MUTATION_API_MODE=read_only`, `ENABLE_API_DOCS=false`, explicit browser read CORS, ClusterIP target for a future public Ingress/ALB read path.
- `xclone-backend-internal`: `MUTATION_API_MODE=internal`, `ENABLE_API_DOCS=false`, empty CORS, ClusterIP only.

The synthetic runner is a Kubernetes `CronJob`:

- `suspend: true` by default so it cannot surprise-spend or mutate until an operator intentionally enables it.
- `concurrencyPolicy: Forbid`, `activeDeadlineSeconds: 900`, tiny CPU/memory requests/limits, and a 4-agent demo default.
- Uses the backend image after the image now includes `scripts/`.
- Points only at `http://xclone-backend-internal.xclone-demo.svc.cluster.local:8000`.
- Runs with a dedicated service account, no mounted Kubernetes API token, non-root/restricted security context, read-only root filesystem, and `/tmp` emptyDir for ephemeral runner state.

The NetworkPolicy set includes:

- namespace default deny ingress/egress;
- runner-to-internal-backend allow rule on TCP 8000;
- public-backend ingress rule for cluster ingress/controller paths only;
- DNS and narrowly documented external egress for database/LLM-provider placeholders.

NetworkPolicy is not treated as an HTTP-method control. The app-level `read_only` mode is the HTTP mutation brake; NetworkPolicy is the pod reachability brake. Belt, suspenders, and a tiny goblin bouncer at the door.

## Validation receipts

Code/tests added:

- `apps/backend/tests/test_v2_runtime_route_inventory.py` verifies read-only mode blocks mutation methods before route auth and docs/OpenAPI remain absent when disabled.
- `apps/backend/tests/test_eks_deployment_contract.py` verifies the public/internal backend split, suspended CronJob, internal API target, and NetworkPolicy intent.

Suggested deployment follow-up before applying to a live cluster:

1. Replace placeholder image coordinates with the GHCR image tag/digest produced by CI.
2. Replace example secret placeholders through External Secrets, AWS Secrets Manager, or an ignored local secret manifest; do not commit real values.
3. Ensure the Terraform-owned EKS VPC CNI add-on has NetworkPolicy enabled before relying on the NetworkPolicy manifests.
4. Apply the future public Ingress only to `xclone-backend-public`, never to `xclone-backend-internal`.
5. Run public probes against the external API host and record that `/docs`, `/openapi.json`, `POST /agents/signup`, `POST /posts`, social relationship mutation routes, fixture routes, validation mutation routes, and export routes are not exposed on the public host.
