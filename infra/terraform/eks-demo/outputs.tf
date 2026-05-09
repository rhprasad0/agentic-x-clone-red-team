output "cluster_name" {
  description = "EKS cluster name for kubectl/Flux handoff."
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint. Keep out of public receipts if it reveals account-specific details."
  value       = aws_eks_cluster.main.endpoint
  sensitive   = true
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded cluster CA data for Kubernetes provider handoff."
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "IAM OIDC provider ARN for IRSA roles."
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "private_subnet_ids" {
  description = "Private subnet IDs for EKS nodes and private workloads."
  value       = values(aws_subnet.private)[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for ALB/NAT placement."
  value       = values(aws_subnet.public)[*].id
}

output "aws_load_balancer_controller_role_arn" {
  description = "IRSA role ARN for kube-system/aws-load-balancer-controller."
  value       = aws_iam_role.aws_lb_controller.arn
}

output "external_secrets_role_arn" {
  description = "IRSA role ARN for external-secrets/external-secrets."
  value       = aws_iam_role.external_secrets.arn
}

output "backend_secrets_read_role_arn" {
  description = "IRSA role ARN for xclone/xclone-backend runtime secret reads."
  value       = aws_iam_role.backend_secrets_read.arn
}

output "rds_endpoint" {
  description = "Private RDS endpoint for app secret creation."
  value       = try(aws_db_instance.postgres[0].endpoint, null)
  sensitive   = true
}

output "rds_master_user_secret_arn" {
  description = "AWS-managed master user secret ARN for the RDS instance."
  value       = try(aws_db_instance.postgres[0].master_user_secret[0].secret_arn, null)
  sensitive   = true
}

output "route53_record_names" {
  description = "Route53 aliases created after ALB handoff. Empty until create_dns_records and ALB variables are supplied."
  value = local.dns_ready ? [
    aws_route53_record.frontend[0].fqdn,
    aws_route53_record.api[0].fqdn,
  ] : []
}

output "cost_guardrail_mode" {
  description = "Reminder that this stack intentionally uses single NAT demo mode and small nodes."
  value       = "single-nat-demo; small managed node group; temporary ttl-hours=${var.ttl_hours}"
}
