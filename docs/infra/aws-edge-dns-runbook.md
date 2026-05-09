# AWS edge, DNS, and TLS runbook

This is a public-safe operator runbook for the temporary x-clone EKS demo edge. It avoids account IDs, raw AWS identifiers, private paths, and secret values.

## Edge shape

- Frontend: `https://xclone.ryans-lab.click`
- API: `https://api.xclone.ryans-lab.click`
- Controller: AWS Load Balancer Controller installed through Terraform-managed Helm release.
- TLS: regional ACM public certificate with DNS validation records in Route53.
- DNS: Terraform-owned Route53 alias records after the Kubernetes Ingress creates an ALB.
- Kubernetes ingress class: `alb`.

The public frontend remains read-only. The API hostname can reach backend read paths and health checks, but mutation and harness routes still require server-side bearer-token authority. Browser CORS must stay read-only, and exposed backend pods should run with `ENABLE_API_DOCS=false` so `/docs` and `/openapi.json` are absent.

## Terraform flow

From `infra/terraform/aws`:

```bash
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan \
  -var='cluster_name=YOUR_EKS_CLUSTER_NAME' \
  -var='domain_name=ryans-lab.click' \
  -var='frontend_hostname=xclone.ryans-lab.click' \
  -var='api_hostname=api.xclone.ryans-lab.click'
```

Apply the ACM/Load Balancer Controller layer only after the target EKS cluster and public hosted zone exist:

```bash
terraform apply \
  -var='cluster_name=YOUR_EKS_CLUSTER_NAME' \
  -var='domain_name=ryans-lab.click' \
  -var='frontend_hostname=xclone.ryans-lab.click' \
  -var='api_hostname=api.xclone.ryans-lab.click'
```

Export the validated certificate ARN for the Ingress manifest without printing account IDs into committed docs:

```bash
terraform output -raw acm_certificate_arn
```

Patch or render `infra/k8s/xclone/alb-ingress.yaml` by replacing `${ACM_CERTIFICATE_ARN}` with that output in a local, uncommitted apply artifact.

## Kubernetes flow

```bash
kubectl apply -f infra/k8s/xclone/service-contract.yaml
kubectl apply -f infra/k8s/xclone/alb-ingress.yaml
kubectl -n xclone get ingress xclone-frontend-public xclone-api-public
```

Wait for the AWS Load Balancer Controller to create the shared ALB for ingress group `xclone-public`:

```bash
kubectl -n xclone get ingress xclone-frontend-public -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
printf '\n'
kubectl -n xclone describe ingress xclone-api-public
```

## Route53 alias handoff

For v1, Terraform owns DNS aliases rather than ExternalDNS. After the ALB exists, look up the ALB hosted-zone ID locally and pass both values back to Terraform:

```bash
ALB_DNS_NAME='REPLACE_WITH_ALB_DNS_NAME_FROM_INGRESS'
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?DNSName=='${ALB_DNS_NAME}'].CanonicalHostedZoneId | [0]" \
  --output text
```

Then plan/apply the aliases:

```bash
terraform plan \
  -var='cluster_name=YOUR_EKS_CLUSTER_NAME' \
  -var="alb_dns_name=${ALB_DNS_NAME}" \
  -var='alb_zone_id=REPLACE_WITH_ALB_ZONE_ID'
```

ExternalDNS remains a later/narrow exception, not the default. If adopted later, restrict it to the `xclone.ryans-lab.click` and `api.xclone.ryans-lab.click` hostnames and document the TXT owner ID.

## Public-safe verification receipts

Use these commands as receipts. Keep the command text and pass/fail summaries public; do not paste raw hosted-zone IDs, account IDs, or full certificate ARNs into public artifacts.

```bash
aws acm describe-certificate \
  --certificate-arn 'REPLACE_WITH_CERTIFICATE_ARN' \
  --query 'Certificate.{Status:Status,DomainName:DomainName,SubjectAlternativeNames:SubjectAlternativeNames,RenewalEligibility:RenewalEligibility}' \
  --output json

aws route53 list-resource-record-sets \
  --hosted-zone-id 'REPLACE_WITH_HOSTED_ZONE_ID' \
  --query "ResourceRecordSets[?Name=='xclone.ryans-lab.click.' || Name=='api.xclone.ryans-lab.click.'].{Name:Name,Type:Type,Alias:AliasTarget.DNSName}" \
  --output json

dig +short xclone.ryans-lab.click
dig +short api.xclone.ryans-lab.click
curl -fsS https://api.xclone.ryans-lab.click/health
curl -fsSI https://xclone.ryans-lab.click/
curl -fsSI https://api.xclone.ryans-lab.click/docs || true
curl -fsSI https://api.xclone.ryans-lab.click/openapi.json || true
```

Expected exposed-backend posture:

- `/health` returns `200` with `status=ok`.
- `/docs` and `/openapi.json` return absent/non-200 when `ENABLE_API_DOCS=false` is set for the exposed API deployment.
- Public read endpoints work without bearer tokens.
- Synthetic mutations and harness routes return `401`/`403` without the right authority token.

## Blockers for live apply

Live DNS/certificate apply is blocked only if one of these is missing after checking AWS and project memory:

- EKS cluster name.
- Route53 public hosted zone for `ryans-lab.click` or its hosted-zone ID.
- Permission to create ACM validation records and Route53 aliases.
- The ALB DNS name/hosted-zone ID after the Kubernetes Ingress has reconciled.
