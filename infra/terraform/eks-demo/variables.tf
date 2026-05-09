variable "aws_region" {
  description = "AWS region for the temporary demo stack."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project name used in resource names and tags."
  type        = string
  default     = "xclone"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "demo"
}

variable "owner_tag" {
  description = "Public-safe owner tag. Use a role/team label, not a personal identifier."
  type        = string
  default     = "project-maintainer"
}

variable "ttl_hours" {
  description = "Expected lifetime for the temporary demo. Used for tagging and teardown reminders."
  type        = number
  default     = 48
}

variable "expires_at" {
  description = "Public-safe expiry note for the temporary demo. Override with an ISO timestamp locally if desired."
  type        = string
  default     = "manual-teardown-required"
}

variable "vpc_cidr" {
  description = "CIDR block for the demo VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "availability_zone_count" {
  description = "Number of AZs for public/private subnets. Single NAT demo mode still creates one NAT gateway."
  type        = number
  default     = 2

  validation {
    condition     = var.availability_zone_count >= 2 && var.availability_zone_count <= 3
    error_message = "Use 2 or 3 AZs for this demo baseline."
  }
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.33"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the EKS public API endpoint. Tighten in local tfvars before apply if possible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  description = "Small managed-node instance types for a handful of demo visitors."
  type        = list(string)
  default     = ["t3.small"]
}

variable "node_desired_size" {
  description = "Desired managed node count for the demo."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum managed node count for the demo."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum managed node count for the demo."
  type        = number
  default     = 3
}

variable "create_rds" {
  description = "Create the private single-AZ PostgreSQL database for the app."
  type        = bool
  default     = true
}

variable "db_instance_class" {
  description = "Small RDS instance class for the temporary demo."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage_gb" {
  description = "Allocated RDS storage in GiB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial app database name."
  type        = string
  default     = "xclone"
}

variable "create_dns_records" {
  description = "Create Route53 aliases after the Kubernetes-created ALB exists and its DNS name/zone id are supplied."
  type        = bool
  default     = false
}

variable "hosted_zone_name" {
  description = "Route53 hosted zone name, e.g. example.com. Leave blank until DNS handoff is ready."
  type        = string
  default     = ""
}

variable "frontend_hostname" {
  description = "Frontend hostname for the public demo."
  type        = string
  default     = "xclone.example.com"
}

variable "api_hostname" {
  description = "Read-only API hostname for the public demo."
  type        = string
  default     = "api.xclone.example.com"
}

variable "alb_dns_name" {
  description = "DNS name of the Kubernetes-created ALB. Set after Flux applies Ingress."
  type        = string
  default     = ""
}

variable "alb_zone_id" {
  description = "Canonical hosted zone ID of the Kubernetes-created ALB. Set after Flux applies Ingress."
  type        = string
  default     = ""
}
