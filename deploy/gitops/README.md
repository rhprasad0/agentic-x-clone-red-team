# x-clone Flux GitOps layout

This directory is a Flux-compatible bootstrap and application manifest layout for the temporary x-clone EKS demo.

It is intentionally public-safe:

- public GHCR image references use placeholders until CI publishes immutable tags;
- Kubernetes manifests reference Secrets Manager / Kubernetes Secret names only, never secret values;
- AWS account-specific IDs, ARNs, certificate ARNs, subnet IDs, security group IDs, and hosted-zone IDs are placeholders;
- Flux live bootstrap write credentials are not included.

## Layout

- `clusters/xclone-demo/` contains cluster-level Flux sources and Kustomizations.
- `platform/controllers/` contains Helm-managed in-cluster controllers owned by Flux after Terraform creates the required AWS/IAM primitives.
- `apps/base/` contains reusable app manifests: namespaces, service accounts, deployments, services, network policies, and secret references.
- `apps/overlays/demo/` patches the base for the small public demo.
- `image-automation/` contains safe image-scan/policy stubs for public GHCR images. Git write-back automation is deliberately omitted until a deploy key or token is provided out-of-band.

## Public boundary

The frontend ingress is public. The API ingress uses an AWS Load Balancer Controller method condition so only `GET`/`HEAD` requests route through the public API service, and only the health/read path prefixes are listed. The synthetic runner is a suspended internal CronJob and talks to the backend ClusterIP service. Keep app-level route hardening/tests in place too; ALB routing is a boundary layer, not a substitute for application authorization.

## Bootstrap handoff

Terraform should create the EKS cluster, OIDC provider, IRSA roles, ACM certificate, Route53 zone lookups, RDS, Secrets Manager records, VPC CNI network-policy configuration, and the AWS Load Balancer Controller IAM role before Flux reconciles these manifests.

A future live bootstrap can point Flux at this repository path:

```text
./deploy/gitops/clusters/xclone-demo
```

Do not commit Flux deploy keys, GitHub tokens, kubeconfigs, AWS account IDs, or rendered secret values.
