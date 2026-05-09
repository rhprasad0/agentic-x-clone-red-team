variable "aws_region" {
  description = "AWS region for the EKS demo stack and regional ACM certificate."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Existing EKS cluster name that will run the x-clone demo workloads."
  type        = string
}

variable "domain_name" {
  description = "Public hosted-zone apex used for demo DNS."
  type        = string
  default     = "ryans-lab.click"
}

variable "frontend_hostname" {
  description = "Public hostname for the read-only frontend."
  type        = string
  default     = "xclone.ryans-lab.click"
}

variable "api_hostname" {
  description = "Public hostname for the bounded API surface."
  type        = string
  default     = "api.xclone.ryans-lab.click"
}

variable "kubernetes_namespace" {
  description = "Namespace used by the x-clone application manifests."
  type        = string
  default     = "xclone"
}

variable "public_zone_id" {
  description = "Optional Route53 public hosted-zone ID. When null, Terraform looks it up by domain_name."
  type        = string
  default     = null
}

variable "alb_dns_name" {
  description = "Optional ALB DNS name emitted by the Kubernetes Ingress. Set after the Ingress exists to let Terraform own Route53 aliases."
  type        = string
  default     = ""
}

variable "alb_zone_id" {
  description = "Optional ALB hosted-zone ID emitted by AWS for the load balancer. Required with alb_dns_name for Terraform-owned aliases."
  type        = string
  default     = ""
}

variable "aws_load_balancer_controller_chart_version" {
  description = "Pinned AWS Load Balancer Controller Helm chart version."
  type        = string
  default     = "1.13.4"
}
