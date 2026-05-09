locals {
  route53_zone_id = coalesce(var.public_zone_id, try(data.aws_route53_zone.public[0].zone_id, null))
  certificate_domains = toset([
    var.frontend_hostname,
    var.api_hostname,
  ])
  create_alb_alias_records = var.alb_dns_name != "" && var.alb_zone_id != ""
}

data "aws_route53_zone" "public" {
  count        = var.public_zone_id == null ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

resource "aws_acm_certificate" "xclone_public" {
  domain_name               = var.frontend_hostname
  subject_alternative_names = [var.api_hostname]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Project   = "x-clone-demo"
    ManagedBy = "terraform"
    Purpose   = "temporary-demo-tls"
  }
}

resource "aws_route53_record" "xclone_certificate_validation" {
  for_each = {
    for dvo in aws_acm_certificate.xclone_public.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = local.route53_zone_id
}

resource "aws_acm_certificate_validation" "xclone_public" {
  certificate_arn         = aws_acm_certificate.xclone_public.arn
  validation_record_fqdns = [for record in aws_route53_record.xclone_certificate_validation : record.fqdn]
}

resource "aws_route53_record" "xclone_alb_alias" {
  for_each = local.create_alb_alias_records ? local.certificate_domains : toset([])

  name    = each.value
  type    = "A"
  zone_id = local.route53_zone_id

  alias {
    evaluate_target_health = true
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
  }
}
