output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint hostname. Not secret, but keep receipts redacted for public artifacts."
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "RDS PostgreSQL port."
  value       = aws_db_instance.postgres.port
}

output "database_name" {
  description = "Initial database name."
  value       = aws_db_instance.postgres.db_name
}

output "rds_security_group_id" {
  description = "Security group attached to the private RDS instance."
  value       = aws_security_group.postgres.id
}

output "rds_master_user_secret_arn" {
  description = "AWS-managed RDS master credential secret ARN. Do not paste the secret value into repo artifacts."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
  sensitive   = true
}

output "app_database_secret_name" {
  description = "Secrets Manager secret name expected by ExternalSecret for backend DATABASE_URL."
  value       = aws_secretsmanager_secret.app_database_url.name
}

output "migration_database_secret_name" {
  description = "Secrets Manager secret name expected by the migration Job ExternalSecret."
  value       = aws_secretsmanager_secret.migration_database_url.name
}

output "external_secrets_read_policy_arn" {
  description = "Attach this policy to the External Secrets Operator IAM role/IRSA subject."
  value       = aws_iam_policy.external_secrets_read_database.arn
}
