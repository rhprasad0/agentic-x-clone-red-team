from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

import app.models as models
from app.db.base import Base

V2_TABLES = {
    "agents",
    "posts",
    "findings",
    "auth_token_hashes",
    "likes",
    "reposts",
    "follows",
    "validation_runs",
    "validation_events",
}


def constraint_names(table_name: str, constraint_type: type) -> set[str]:
    return {
        constraint.name
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


def index_names(table_name: str) -> set[str]:
    return {
        index.name
        for index in Base.metadata.tables[table_name].indexes
        if isinstance(index, Index)
    }


def column_names(table_name: str) -> set[str]:
    return {column.name for column in Base.metadata.tables[table_name].columns}


def test_v2_models_are_imported_into_base_metadata() -> None:
    assert models.AuthTokenHash.__tablename__ == "auth_token_hashes"
    assert models.Like.__tablename__ == "likes"
    assert models.Repost.__tablename__ == "reposts"
    assert models.Follow.__tablename__ == "follows"
    assert models.ValidationRun.__tablename__ == "validation_runs"
    assert models.ValidationEvent.__tablename__ == "validation_events"

    assert V2_TABLES.issubset(set(Base.metadata.tables))


def test_agent_post_and_finding_models_use_v2_canonical_columns() -> None:
    agent_columns = column_names("agents")
    post_columns = column_names("posts")
    finding_columns = column_names("findings")

    assert {
        "handle_normalized",
        "persona_summary",
        "avatar_seed",
        "is_fixture",
        "disabled_at",
        "updated_at",
    }.issubset(agent_columns)
    assert "uq_agents_handle_normalized" in constraint_names("agents", UniqueConstraint)
    assert {
        "ix_agents_handle_normalized_id",
        "ix_agents_created_at_id",
    }.issubset(index_names("agents"))

    assert {
        "text",
        "root_post_id",
        "reply_depth",
        "quote_post_id",
        "client_request_id",
    }.issubset(post_columns)
    assert "body" not in post_columns
    assert "scenario_run_id" not in post_columns
    assert {
        "ck_posts_text_length",
        "ck_posts_reply_depth",
        "ck_posts_not_own_parent",
    }.issubset(constraint_names("posts", CheckConstraint))
    assert "uq_posts_author_client_request_id" in index_names("posts")

    assert {
        "validation_run_id",
        "severity",
        "status",
        "affected_route_class",
        "affected_object_class",
        "redacted_evidence_summary",
        "fix_ref",
        "regression_ref",
        "residual_risk",
        "created_at",
        "updated_at",
    }.issubset(finding_columns)
    assert "scenario_run_id" not in finding_columns


def test_auth_token_hash_model_has_no_plaintext_token_surface() -> None:
    columns = column_names("auth_token_hashes")

    assert {
        "id",
        "token_hash",
        "token_prefix",
        "authority_type",
        "agent_id",
        "label",
        "enabled",
        "revoked_at",
        "created_at",
        "last_used_at",
    } == columns
    assert "token" not in columns
    assert "token_plaintext" not in columns
    assert "uq_auth_token_hashes_token_hash" in constraint_names(
        "auth_token_hashes", UniqueConstraint
    )
    assert "ix_auth_token_hashes_authority_enabled" in index_names("auth_token_hashes")


def test_social_edge_models_have_uniqueness_checks_and_ordering_indexes() -> None:
    assert {
        "id",
        "agent_id",
        "post_id",
        "client_request_id",
        "created_at",
    } == column_names("likes")
    assert {"uq_likes_agent_post"}.issubset(constraint_names("likes", UniqueConstraint))
    assert {
        "ix_likes_post_created_at_id",
        "ix_likes_agent_created_at_id",
        "uq_likes_agent_client_request_id",
    }.issubset(index_names("likes"))

    assert {
        "id",
        "agent_id",
        "post_id",
        "client_request_id",
        "created_at",
    } == column_names("reposts")
    assert {"uq_reposts_agent_post"}.issubset(constraint_names("reposts", UniqueConstraint))
    assert {
        "ix_reposts_post_created_at_id",
        "ix_reposts_agent_created_at_id",
        "uq_reposts_agent_client_request_id",
    }.issubset(index_names("reposts"))

    assert {
        "id",
        "follower_agent_id",
        "followee_agent_id",
        "client_request_id",
        "created_at",
    } == column_names("follows")
    assert {"uq_follows_follower_followee"}.issubset(
        constraint_names("follows", UniqueConstraint)
    )
    assert "ck_follows_not_self" in constraint_names("follows", CheckConstraint)
    assert {
        "ix_follows_followee_created_at_id",
        "ix_follows_follower_created_at_id",
        "uq_follows_follower_client_request_id",
    }.issubset(index_names("follows"))


def test_validation_models_link_events_and_findings_to_validation_runs() -> None:
    assert {
        "id",
        "scenario_run_id",
        "scenario_id",
        "status",
        "objective",
        "metadata_json",
        "created_at",
        "updated_at",
    } == column_names("validation_runs")
    assert "uq_validation_runs_scenario_run_id" in constraint_names(
        "validation_runs", UniqueConstraint
    )

    assert {
        "id",
        "validation_run_id",
        "event_type",
        "redacted_summary",
        "metadata_json",
        "created_at",
        "updated_at",
    } == column_names("validation_events")
    assert {
        "ix_validation_events_validation_run_created_at_id",
        "ix_validation_events_event_type",
    }.issubset(index_names("validation_events"))

    finding_fks = [
        constraint
        for constraint in Base.metadata.tables["findings"].constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert any(fk.referred_table.name == "validation_runs" for fk in finding_fks)
