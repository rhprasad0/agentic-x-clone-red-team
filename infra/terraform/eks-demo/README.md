# x-clone EKS demo Terraform baseline

This directory contains the temporary, small-demo Terraform baseline for the x-clone public credibility deployment. It is intentionally production-shaped, not production-sized: one VPC, public/private subnets across two AZs, a single NAT gateway demo tradeoff, a small EKS managed node group, EKS add-ons, OIDC/IRSA roles, private single-AZ RDS PostgreSQL, and a deferred Route53 alias handoff for the Kubernetes-created ALB.

## What Terraform owns

- VPC, public/private subnets, internet gateway, one NAT gateway, and route tables.
- EKS cluster, managed node group, and EKS add-ons.
- VPC CNI network-policy enablement through the Terraform-owned EKS add-on configuration.
- IAM cluster/node roles and IAM OIDC provider.
- IRSA roles for AWS Load Balancer Controller and External Secrets.
- Private single-AZ RDS PostgreSQL with AWS-managed master user secret.
- Optional Route53 alias records once Flux has created the ALB and the ALB DNS name/zone ID are known.

## What Flux/app deployment owns later

- Namespaces, service accounts, HelmReleases, Kustomizations, Deployments, Services, Ingress, NetworkPolicies, ExternalSecret objects, runner CronJob, and app configuration.
- AWS Load Balancer Controller installation that uses the `aws_load_balancer_controller_role_arn` output.
- External Secrets installation that uses the `external_secrets_role_arn` output.
- The ALB-producing Ingress. After it exists, feed its DNS name and hosted-zone ID back into Terraform for Route53 aliases, or intentionally choose ExternalDNS as a narrow exception in the GitOps layer.

## Local usage

```bash
cd infra/terraform/eks-demo
cp terraform.tfvars.example terraform.tfvars
terraform fmt -recursive
terraform init
terraform validate
terraform plan
```

`terraform.tfvars` and all state/plan files are ignored. Keep real hosted-zone names, account-specific IDs, local operator IPs, and live plan output out of committed artifacts.

## Apply posture

Apply is allowed for the active demo run if prerequisites and validation are clean. Before apply, verify:

- AWS credentials point at the intended demo account/region.
- `cluster_endpoint_public_access_cidrs` is acceptable for the operator context.
- The cost tradeoff is intentional: EKS control plane, one NAT gateway, small EC2 nodes, ALB after Flux, RDS, logs, and any retained snapshots still cost money.
- The public app route remains bounded: public frontend/read API only; mutation/runner routes stay internal.

## Teardown posture

Collect redacted receipts first, suspend/delete runner workloads, delete Flux Ingress and wait for ALB cleanup, then run:

```bash
terraform plan -destroy
terraform destroy
```

After destroy, verify no EKS cluster, ALB, NAT gateway, RDS instance, unattached volume, or unintended snapshot remains.
