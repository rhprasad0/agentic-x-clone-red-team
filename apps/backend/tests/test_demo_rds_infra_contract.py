from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TERRAFORM_DIR = REPO_ROOT / "infra" / "terraform" / "demo-rds"
K8S_DIR = REPO_ROOT / "infra" / "k8s" / "demo" / "database"


def test_demo_rds_terraform_uses_private_small_managed_postgres() -> None:
    main_tf = (TERRAFORM_DIR / "main.tf").read_text()
    variables_tf = (TERRAFORM_DIR / "variables.tf").read_text()
    outputs_tf = (TERRAFORM_DIR / "outputs.tf").read_text()

    assert 'engine         = "postgres"' in main_tf
    assert 'publicly_accessible    = false' in main_tf
    assert 'multi_az               = false' in main_tf
    assert 'manage_master_user_password = true' in main_tf
    assert 'parameter_group_name = aws_db_parameter_group.postgres.name' in main_tf
    assert 'rds.log_retention_period' in main_tf
    assert 'enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]' in main_tf
    assert 'security_groups = [var.eks_cluster_security_group_id]' in main_tf
    assert 'default     = "db.t4g.micro"' in variables_tf
    assert 'default     = 20' in variables_tf
    assert 'default     = 1' in variables_tf
    assert 'sensitive   = true' in outputs_tf


def test_external_secret_and_migration_job_reference_secret_names_without_values() -> None:
    external_secrets = (K8S_DIR / "external-secrets.yaml").read_text()
    migration_job = (K8S_DIR / "migration-job.yaml").read_text()
    readme = (REPO_ROOT / "infra" / "README.md").read_text()

    assert "x-clone-demo/postgres/app" in external_secrets
    assert "x-clone-demo/postgres/migrations" in external_secrets
    assert "property: DATABASE_URL" in external_secrets
    assert "serviceAccountRef:" in external_secrets
    assert "alembic.ini" in migration_job
    assert "upgrade" in migration_job
    assert "x-clone-migration-database" in migration_job
    assert "postgresql+psycopg://USERNAME:PASSWORD@HOSTNAME:5432/agentic_x_clone" in readme

    combined = "\n".join([external_secrets, migration_job, readme])
    forbidden_literals = [
        "postgres_password_placeholder@",
        "bridge_local_key_placeholder",
        "agent_alex_fixture_token_placeholder",
    ]
    for literal in forbidden_literals:
        assert literal not in combined
