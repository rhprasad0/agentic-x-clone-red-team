# x-clone Kubernetes edge manifests

These manifests define the public ALB ingress contract for the temporary x-clone EKS demo.

Apply order:

1. `service-contract.yaml` after workload Deployments exist or alongside their labels.
2. `alb-ingress.yaml` after Terraform has produced a validated ACM certificate ARN.

The ingress manifests intentionally keep DNS ownership out of Kubernetes for v1. Terraform owns the Route53 aliases after the AWS Load Balancer Controller creates the ALB and the operator passes the ALB DNS name plus hosted-zone ID into `infra/terraform/aws`.

Public API boundary:

- `xclone.ryans-lab.click` serves the read-only frontend.
- `api.xclone.ryans-lab.click` reaches the FastAPI service for demo/read paths and health checks.
- Mutation and harness routes remain protected by backend bearer-token authority checks; browser CORS is read-only and `ENABLE_API_DOCS=false` is required for exposed backend pods.
- Do not mount synthetic-agent or harness bearer tokens into the frontend container.
