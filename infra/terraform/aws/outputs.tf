output "acm_certificate_arn" {
  description = "Validated ACM certificate ARN for the x-clone frontend and API hostnames. Use as the ALB Ingress certificate annotation."
  value       = aws_acm_certificate_validation.xclone_public.certificate_arn
}

output "route53_zone_id_source" {
  description = "Whether the public hosted zone was supplied by variable or discovered by name."
  value       = var.public_zone_id == null ? "looked-up-by-domain-name" : "provided-by-variable"
}

output "alb_alias_records_enabled" {
  description = "True only after alb_dns_name and alb_zone_id are supplied from the created ALB."
  value       = local.create_alb_alias_records
}

output "aws_load_balancer_controller_role_name" {
  description = "IAM role name used by the aws-load-balancer-controller service account."
  value       = aws_iam_role.aws_load_balancer_controller.name
}
