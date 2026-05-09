resource "aws_security_group" "rds" {
  count = var.create_rds ? 1 : 0

  name        = "${local.name_prefix}-rds"
  description = "Private PostgreSQL access from the EKS cluster security group."
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL from EKS control plane and managed node security groups."
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [
      aws_security_group.eks_cluster.id,
      aws_eks_cluster.main.vpc_config[0].cluster_security_group_id,
    ]
  }

  egress {
    description = "Allow database egress for AWS-managed operations."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-rds"
  }
}

resource "aws_db_subnet_group" "main" {
  count = var.create_rds ? 1 : 0

  name       = "${local.name_prefix}-db"
  subnet_ids = values(aws_subnet.private)[*].id

  tags = {
    Name = "${local.name_prefix}-db"
  }
}

resource "aws_db_instance" "postgres" {
  count = var.create_rds ? 1 : 0

  identifier                          = "${local.name_prefix}-postgres"
  engine                              = "postgres"
  engine_version                      = "16"
  instance_class                      = var.db_instance_class
  allocated_storage                   = var.db_allocated_storage_gb
  storage_type                        = "gp3"
  db_name                             = var.db_name
  username                            = "xclone_admin"
  manage_master_user_password         = true
  iam_database_authentication_enabled = true
  db_subnet_group_name                = aws_db_subnet_group.main[0].name
  vpc_security_group_ids              = [aws_security_group.rds[0].id]
  multi_az                            = false
  publicly_accessible                 = false
  deletion_protection                 = false
  skip_final_snapshot                 = true
  apply_immediately                   = true
  backup_retention_period             = 1
  auto_minor_version_upgrade          = true

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}
