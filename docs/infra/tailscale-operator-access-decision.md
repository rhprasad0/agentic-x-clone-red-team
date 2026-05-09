# Tailscale operator access decision

This decision record captures the public-safe design for the tailnet-only backend mutation lane. It intentionally does not include Tailscale OAuth values, auth URLs, tailnet names, users, device identifiers, home IPs, raw traces, or private runtime outputs.

## Documentation checked

- Context7 `/websites/tailscale`: Tailscale Kubernetes Operator supports exposing workloads with a `Service` using `loadBalancerClass: tailscale` or an `Ingress` using `ingressClassName: tailscale`; Helm installation uses private OAuth configuration; Funnel is a separate explicit public-internet exposure mode.
- AWS MCP EKS documentation: AWS Load Balancer Controller provisions ALBs for Kubernetes `Ingress` resources and NLBs for Kubernetes `Service type=LoadBalancer` resources, reinforcing that the backend mutation lane should not use the public AWS load-balancer path.

## Decision

Use a Flux-owned Tailscale Kubernetes Operator with private credentials supplied by a live cluster-local Secret in the operator namespace.

Expose the full backend mutation lane with a dedicated Tailscale `LoadBalancer` Service in the application namespace:

- `type: LoadBalancer`
- `loadBalancerClass: tailscale`
- generic public-safe resource naming, such as `xclone-backend-operator-tailnet`
- selector matching the internal backend pods
- no public Route53 record
- no public ALB listener
- no Tailscale Funnel annotation or policy grant

## Rationale

A Tailscale `Ingress` is a valid operator pattern, but the first implementation should use a Tailscale `LoadBalancer` Service because the local runner only needs a direct full-backend HTTP target. The Service path avoids extra L7/TLS/MagicDNS certificate coupling, is easier to revoke by deleting one Kubernetes object, and keeps the operator mutation lane visually distinct from the existing public ALB `Ingress` resources.

Terraform-created Kubernetes Secret wiring is not the first-choice pattern because it increases state sensitivity and adds an ownership seam between Terraform and Flux. Manual Helm installation is only a break-glass diagnostic path because it does not provide durable GitOps persistence.

## Expected public tracked changes

Likely implementation files:

- `deploy/gitops/platform/controllers/` for Tailscale namespace/source/HelmRelease wiring
- `deploy/gitops/platform/controllers/kustomization.yaml` to include the operator resources
- `deploy/gitops/apps/base/` for the tailnet-only backend Service manifest
- `deploy/gitops/apps/base/kustomization.yaml` if the Service lives in a new manifest

Tracked files may reference Kubernetes object names and placeholder key names. They must not contain real OAuth values, tailnet names, users, device IDs, auth URLs, home IPs, bearer tokens, or private runtime output.

## Private live objects

The private side of the implementation is expected to include:

- a Tailscale OAuth or federated identity credential scoped to the Kubernetes Operator;
- a cluster-local Kubernetes Secret in the operator namespace containing the credential values;
- tailnet policy/tag ownership that permits the operator tag to own the required service proxy tags;
- ignored local runner configuration pointing at the tailnet-only backend URL.

Only object names and redacted shape should be recorded in public artifacts.

## Rollback and revocation

1. Remove or suspend the tailnet backend `LoadBalancer` Service and reconcile Flux so the operator proxy disappears.
2. Verify that no public ALB, public Route53 record, or Tailscale Funnel exposure exists for the mutation lane.
3. If the lane should be closed completely, suspend or delete the Tailscale Operator HelmRelease and reconcile/prune unneeded operator resources.
4. Delete the cluster-local OAuth Secret.
5. Revoke or disable the corresponding Tailscale OAuth/federated credential.
6. Remove or tighten operator tag grants in tailnet policy.
7. Optionally log the operator workstation out of Tailscale if local access should be closed too.
8. Re-run sanitized checks showing public mutation denial, no Funnel, and no unintended changes to EKS, RDS, VPC, DNS, ACM, Route53, Secrets Manager, IAM, AWS Load Balancer Controller, or public frontend/read API resources.

## Infra preservation boundary

This design is additive at the Kubernetes/Flux layer. It does not require destroying or recreating EKS, RDS, VPC, DNS, ACM, Route53, Secrets Manager, IAM, the AWS Load Balancer Controller, or existing public frontend/read API resources.
