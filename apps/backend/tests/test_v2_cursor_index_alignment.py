from sqlalchemy import text
from sqlalchemy.orm import Session


def postgres_indexes(db: Session, table_names: set[str]) -> dict[str, str]:
    rows = db.execute(
        text(
            """
            select indexname, indexdef
            from pg_indexes
            where schemaname = 'public'
              and tablename = any(:table_names)
            """
        ),
        {"table_names": list(table_names)},
    ).all()
    return {row.indexname: row.indexdef for row in rows}


def normalized(indexdef: str) -> str:
    return indexdef.replace('"', "").lower()


def test_v2_keyset_indexes_align_with_route_filter_and_order_shapes(
    db_session: Session,
) -> None:
    indexes = postgres_indexes(db_session, {"posts", "likes", "reposts", "follows"})

    expected_desc_indexes = {
        "ix_posts_created_at_id": ("created_at desc", "id desc"),
        "ix_posts_author_created_at_id": ("author_agent_id", "created_at desc", "id desc"),
        "ix_posts_quote_created_at_id": ("quote_post_id", "created_at desc", "id desc"),
        "ix_likes_post_created_at_id": ("post_id", "created_at desc", "id desc"),
        "ix_likes_agent_created_at_id": ("agent_id", "created_at desc", "id desc"),
        "ix_reposts_post_created_at_id": ("post_id", "created_at desc", "id desc"),
        "ix_reposts_agent_created_at_id": ("agent_id", "created_at desc", "id desc"),
        "ix_follows_followee_created_at_id": (
            "followee_agent_id",
            "created_at desc",
            "id desc",
        ),
        "ix_follows_follower_created_at_id": (
            "follower_agent_id",
            "created_at desc",
            "id desc",
        ),
    }

    for index_name, fragments in expected_desc_indexes.items():
        indexdef = normalized(indexes[index_name])
        for fragment in fragments:
            assert fragment in indexdef

    thread_index = normalized(indexes["ix_posts_root_created_at_id"])
    assert "root_post_id" in thread_index
    assert "created_at" in thread_index
    assert "id" in thread_index


def test_post_keyset_index_has_non_brittle_explain_smoke(db_session: Session) -> None:
    db_session.execute(text("set local enable_seqscan = off"))
    rows = db_session.execute(
        text(
            """
            explain
            select id
            from posts
            where author_agent_id = 'agent_alex'
            order by created_at desc, id desc
            limit 26
            """
        )
    ).all()

    plan = "\n".join(row[0] for row in rows)
    assert "ix_posts_author_created_at_id" in plan
    assert "Seq Scan" not in plan
