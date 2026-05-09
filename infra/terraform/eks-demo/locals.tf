locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project        = var.project_name
    Environment    = var.environment
    Owner          = var.owner_tag
    ManagedBy      = "terraform"
    Purpose        = "temporary-eks-demo"
    PublicEvidence = "false"
    ttl-hours      = tostring(var.ttl_hours)
    expires-at     = var.expires_at
  }

  azs = slice(data.aws_availability_zones.available.names, 0, var.availability_zone_count)
}

data "aws_availability_zones" "available" {
  state = "available"
}
