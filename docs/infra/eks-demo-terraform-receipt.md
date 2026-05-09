# EKS demo Terraform receipt

Date: 2026-05-09

Scope: temporary x-clone EKS demo phase-1 baseline.

## Sources consulted

- Graphiti group `x-clone`: managed node group, single NAT, OIDC/IRSA, Route53/Flux handoff, and temporary cost-control facts.
- Honcho: latest EKS/GitOps answers, including small-demo sizing, direct execution, live AWS/GitHub CLI availability, single NAT demo mode, and no need to wait for terminal closure.
- AWS docs: EKS IRSA/OIDC, EKS managed node groups, EKS VPC CNI network-policy configuration, VPC NAT gateway patterns, and Route53 aliases to ELB/ALB.
- Context7: `/hashicorp/terraform-provider-aws` EKS cluster/node group examples and `/websites/fluxcd_io_flux` bootstrap/GitOps handoff docs.
- Current repo files: README, architecture docs, public-safety policy, and existing local app scope docs.

## Terraform delivered

Path: `infra/terraform/eks-demo`

Terraform owns:

- VPC with public/private subnets across two AZs.
- Single NAT gateway demo mode for private subnet egress.
- EKS cluster with public/private API endpoints and control-plane logging.
- Small EKS managed node group: `t3.small`, min 1, desired 2, max 3.
- EKS add-ons: VPC CNI with network-policy configuration, CoreDNS, kube-proxy, and EKS Pod Identity Agent.
- IAM cluster/node roles, EKS OIDC provider, and IRSA roles for AWS Load Balancer Controller and External Secrets.
- Private single-AZ PostgreSQL RDS: `db.t4g.micro`, not publicly accessible, AWS-managed master user secret.
- Deferred Route53 aliases for the Kubernetes/Flux-created ALB once ALB DNS name and hosted-zone ID are supplied.

Local-only files generated during validation/apply are ignored by `.gitignore`:

- `terraform.tfvars`
- `.terraform/`
- Terraform state files
- Terraform plan files

## Validation and apply receipts

Commands run from `infra/terraform/eks-demo`:

```bash
terraform fmt -recursive
terraform init -input=false
terraform validate
terraform plan -input=false -no-color
terraform apply -auto-approve -input=false -no-color
terraform plan -input=false -no-color
```

Results:

- `terraform fmt -recursive`: passed.
- `terraform init -input=false`: passed; provider lock file created.
- `terraform validate`: passed.
- Pre-apply plan: `38 to add, 0 to change, 0 to destroy`.
- Apply: complete; `38 added, 0 changed, 0 destroyed`.
- Post-apply plan: no changes; real infrastructure matches configuration.

Apply used an ignored local `terraform.tfvars` that tightened the EKS public API endpoint CIDR from the committed placeholder default to the current operator `/32`. The CIDR is intentionally not committed or reproduced here.

## Live AWS verification

Public-safe AWS CLI checks after apply:

```text
EKS cluster: ACTIVE, Kubernetes 1.33, public endpoint enabled, private endpoint enabled, logging enabled.
Managed node group: ACTIVE, instance type t3.small, desired 2, min 1, max 3, no health issues.
EKS add-ons: vpc-cni ACTIVE, coredns ACTIVE, kube-proxy ACTIVE, eks-pod-identity-agent ACTIVE.
RDS: available, postgres, db.t4g.micro, publiclyAccessible=false, multiAZ=false.
NAT gateways with demo tag/name: count=1, state=available.
Route53 aliases: intentionally not created yet; waiting for Flux/Kubernetes ALB handoff values.
```

## Notes and caveats

- `kubectl` is not installed in this worker environment, so Kubernetes pod-level verification was not run here. AWS-side EKS/nodegroup/add-on status checks are green.
- CoreDNS briefly reported `DEGRADED` with `InsufficientNumberOfReplicas` while the node group was still becoming active; it became `ACTIVE` before apply completed.
- Route53 records are phase two. Terraform is ready to create them once the Flux-owned Ingress creates the ALB and the ALB DNS name/hosted-zone ID are supplied.
- This stack now costs real AWS money. Keep the TTL/cost tags, collect receipts, and tear down when the demo is done. Tiny cluster, still a money goblin.
