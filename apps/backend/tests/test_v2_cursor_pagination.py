from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import Settings
from app.models.post import Post
from app.services.cursors import (
    CursorPosition,
    CursorScope,
    apply_keyset_pagination,
    decode_cursor,
    encode_cursor,
    normalize_limit,
)

NOW = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)


def cursor_settings() -> Settings:
    return Settings(
        v2_cursor_signing_key="cursor_signing_key_placeholder",
        v2_cursor_ttl_seconds=60,
    )


def assert_bad_cursor(exc_info: pytest.ExceptionInfo[HTTPException]) -> None:
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid cursor"


def test_cursor_limit_defaults_and_bounds_are_service_defined() -> None:
    settings = cursor_settings()

    assert normalize_limit(None, settings=settings) == 25
    assert normalize_limit(1, settings=settings) == 1
    assert normalize_limit(100, settings=settings) == 100

    for value in (0, 101):
        with pytest.raises(HTTPException) as exc_info:
            normalize_limit(value, settings=settings)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid limit"


def test_signed_cursor_round_trips_and_is_bound_to_route_actor_filters_and_direction() -> None:
    settings = cursor_settings()
    position = CursorPosition(created_at=NOW, item_id="post_synthetic_boundary")
    scope = CursorScope(
        route_key="GET /timelines/home",
        actor_key="synthetic_agent:agent_alex",
        filters={"include_replies": False, "author": "agent_alex"},
        direction="desc",
    )

    cursor = encode_cursor(position, scope, settings=settings, now=NOW)

    assert "post_synthetic_boundary" not in cursor
    assert "2026-05-07" not in cursor
    assert decode_cursor(cursor, scope, settings=settings, now=NOW) == position

    tampered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
    with pytest.raises(HTTPException) as exc_info:
        decode_cursor(tampered, scope, settings=settings, now=NOW)
    assert_bad_cursor(exc_info)

    bound_scopes = [
        CursorScope("GET /timelines/public", scope.actor_key, scope.filters, "desc"),
        CursorScope(scope.route_key, "synthetic_agent:agent_mira", scope.filters, "desc"),
        CursorScope(scope.route_key, scope.actor_key, {"include_replies": True}, "desc"),
        CursorScope(scope.route_key, scope.actor_key, scope.filters, "asc"),
    ]
    for mismatched_scope in bound_scopes:
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor(cursor, mismatched_scope, settings=settings, now=NOW)
        assert_bad_cursor(exc_info)


def test_malformed_and_expired_cursors_fail_closed_with_generic_400() -> None:
    settings = cursor_settings()
    scope = CursorScope("GET /timelines/public", "public", {"include_replies": False}, "desc")
    position = CursorPosition(created_at=NOW, item_id="post_synthetic_boundary")
    expired = encode_cursor(
        position,
        scope,
        settings=settings,
        now=NOW - timedelta(seconds=120),
    )

    for cursor in ("not-base64-cursor", "%", "☃", expired):
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor(cursor, scope, settings=settings, now=NOW)
        assert_bad_cursor(exc_info)


def test_keyset_statement_uses_stable_desc_order_without_offset_fallback() -> None:
    position = CursorPosition(created_at=NOW, item_id="post_synthetic_boundary")

    statement = apply_keyset_pagination(
        select(Post),
        Post,
        position=position,
        direction="desc",
        limit=25,
    )
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    assert "ORDER BY posts.created_at DESC, posts.id DESC" in compiled
    assert "OFFSET" not in compiled.upper()
    assert "posts.created_at <" in compiled
    assert "posts.created_at =" in compiled
    assert "posts.id <" in compiled
    assert "LIMIT 26" in compiled
