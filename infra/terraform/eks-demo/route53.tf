locals {
  dns_ready = var.create_dns_records && var.hosted_zone_name != "" && var.alb_dns_name != "" && var.alb_zone_id != ""
}

data "aws_route53_zone" "public" {
  count = local.dns_ready ? 1 : 0

  name         = var.hosted_zone_name
  private_zone = false
}

resource "aws_route53_record" "frontend" {
  count = local.dns_ready ? 1 : 0

  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.frontend_hostname
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "api" {
  count = local.dns_ready ? 1 : 0

  zone_id = data.aws_route53_zone.public[0].zone_id
  name    = var.api_hostname
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
