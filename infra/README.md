# x-clone demo infrastructure

This directory contains public-safe infrastructure scaffolding for the temporary x-clone EKS demo. It intentionally contains references, resource shapes, and placeholder IDs only; do not commit AWS account IDs, ARNs, secret values, private logs, or local credential paths.

## Database slice

`terraform/demo-rds` provisions a small private single-AZ RDS PostgreSQL instance for a short-lived portfolio demo:

- PostgreSQL 16, `db.t4g.micro` by default, gp3 storage starting at 20 GiB with a 50 GiB autoscaling cap.
- Private subnet group only; `publicly_accessible = false`.
- Security group ingress limited to the supplied EKS cluster/node security group on TCP 5432.
- One-day automated backups, three-day PostgreSQL/upgrade log retention, encrypted storage, and no deletion protection by default for teardown hygiene.
- A PostgreSQL parameter group sets `rds.log_retention_period` from the Terraform log-retention variable.
- RDS-managed master password in Secrets Manager; no password values are represented in Terraform files or outputs.
- Named Secrets Manager containers expected by Kubernetes External Secrets:
  - `x-clone-demo/postgres/app` with JSON property `DATABASE_URL` for the backend runtime.
  - `x-clone-demo/postgres/migrations` with JSON property `DATABASE_URL` for the migration Job.

`k8s/demo/database` contains External Secrets references and a one-shot Alembic migration Job. The Job should run before a backend rollout and should be triggered intentionally by the release system (for example a Helm hook or a Flux/Kustomize job-name/image-tag change). It does not expose database credentials in manifests.

## Local apply notes

1. Copy `infra/terraform/demo-rds/terraform.tfvars.example` to an ignored local `terraform.tfvars` or pass values through CI variables.
2. Fill in demo VPC/private subnet/security-group IDs locally only.
3. Run:

```bash
cd infra/terraform/demo-rds
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
```

4. After apply, populate Secrets Manager values out-of-band. The expected JSON shape is:

```json
{"DATABASE_URL":"postgresql+psycopg://USERNAME:PASSWORD@HOSTNAME:5432/agentic_x_clone"}
```

Use the RDS endpoint and generated credential secret locally/CI-side. Never paste the resulting value into repo files, PRs, receipts, Slack, or public docs.
