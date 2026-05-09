variable "project" {
  description = "Project tag and resource-name prefix."
  type        = string
  default     = "x-clone"
}

variable "environment" {
  description = "Short environment name for this temporary demo."
  type        = string
  default     = "demo"
}

variable "aws_region" {
  description = "AWS region for the RDS instance and Secrets Manager references."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID containing the private EKS subnets."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the RDS subnet group. Use the demo VPC private subnets, not public subnets. RDS subnet groups require subnets in at least two Availability Zones even when the DB instance is single-AZ."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "Provide at least two private subnet IDs for the RDS subnet group."
  }
}

variable "eks_cluster_security_group_id" {
  description = "EKS cluster or worker-node security group allowed to reach PostgreSQL on 5432."
  type        = string
}

variable "database_name" {
  description = "Initial PostgreSQL database name for the backend."
  type        = string
  default     = "agentic_x_clone"
}

variable "database_username" {
  description = "Master/application bootstrap username. Password is generated and managed by RDS in Secrets Manager."
  type        = string
  default     = "xclone_app"
}

variable "db_instance_class" {
  description = "Small temporary-demo RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage_gb" {
  description = "Initial gp3 storage in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage_gb" {
  description = "Storage autoscaling cap in GiB for demo safety."
  type        = number
  default     = 50
}

variable "backup_retention_days" {
  description = "Automated backup retention. Keep small but nonzero for demo rollback evidence."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention for RDS PostgreSQL logs."
  type        = number
  default     = 3
}

variable "deletion_protection" {
  description = "Keep false for temporary demo teardown unless promoting this stack."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Temporary demo default. Set false before any longer-lived/shared data use."
  type        = bool
  default     = true
}

variable "ttl_hours" {
  description = "Human-readable TTL tag for temporary-demo cost hygiene."
  type        = number
  default     = 72
}

variable "expires_at" {
  description = "Human-readable expiry timestamp tag, e.g. 2026-05-12T00:00:00Z."
  type        = string
  default     = "set-before-apply"
}

variable "owner" {
  description = "Non-PII owner tag value for demo resources."
  type        = string
  default     = "portfolio-demo"
}
