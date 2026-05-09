provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix         = "${var.project}-${var.environment}"
  app_database_secret = "${local.name_prefix}/postgres/app"
  migration_secret    = "${local.name_prefix}/postgres/migrations"
  common_tags = {
    Project        = var.project
    Environment    = var.environment
    Component      = "database"
    ManagedBy      = "terraform"
    Owner          = var.owner
    PublicEvidence = "false"
    ttl-hours      = tostring(var.ttl_hours)
    expires-at     = var.expires_at
  }
}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

resource "aws_db_subnet_group" "postgres" {
  name       = "${local.name_prefix}-postgres"
  subnet_ids = var.private_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres-subnets"
  })
}

resource "aws_security_group" "postgres" {
  name        = "${local.name_prefix}-postgres"
  description = "Private PostgreSQL access from the demo EKS cluster only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from EKS cluster/workers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_cluster_security_group_id]
  }

  egress {
    description = "Database-initiated egress limited to the demo VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

resource "aws_cloudwatch_log_group" "postgres" {
  name              = "/aws/rds/instance/${local.name_prefix}-postgres/postgresql"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_db_parameter_group" "postgres" {
  name        = "${local.name_prefix}-postgres16"
  family      = "postgres16"
  description = "x-clone temporary demo PostgreSQL parameters"

  parameter {
    name  = "rds.log_retention_period"
    value = tostring(var.log_retention_days * 1440)
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres16"
  })
}

resource "aws_db_instance" "postgres" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  db_name  = var.database_name
  username = var.database_username

  parameter_group_name = aws_db_parameter_group.postgres.name

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = var.backup_retention_days
  backup_window           = "08:00-08:30"
  maintenance_window      = "sun:09:00-sun:09:30"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  deletion_protection             = var.deletion_protection
  skip_final_snapshot             = var.skip_final_snapshot
  copy_tags_to_snapshot           = true

  manage_master_user_password = true

  depends_on = [aws_cloudwatch_log_group.postgres]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

resource "aws_secretsmanager_secret" "app_database_url" {
  name        = local.app_database_secret
  description = "Placeholder container for x-clone demo backend DATABASE_URL. Populate out-of-band from RDS endpoint + generated credentials; never commit the value."

  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    SecretPurpose = "backend-database-url"
  })
}

resource "aws_secretsmanager_secret" "migration_database_url" {
  name        = local.migration_secret
  description = "Placeholder container for x-clone demo migration DATABASE_URL. May point at same database with least-privileged migration credentials; never commit the value."

  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    SecretPurpose = "migration-database-url"
  })
}

data "aws_iam_policy_document" "external_secrets_read_database" {
  statement {
    sid = "ReadXCloneDemoDatabaseSecrets"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      aws_db_instance.postgres.master_user_secret[0].secret_arn,
      aws_secretsmanager_secret.app_database_url.arn,
      aws_secretsmanager_secret.migration_database_url.arn,
    ]
  }
}

resource "aws_iam_policy" "external_secrets_read_database" {
  name        = "${local.name_prefix}-external-secrets-database-read"
  description = "Allow External Secrets Operator to read x-clone demo database secrets only."
  policy      = data.aws_iam_policy_document.external_secrets_read_database.json

  tags = local.common_tags
}
