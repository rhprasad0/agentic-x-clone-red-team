from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event, Lock

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.models.idempotency import IdempotencyRecord
from app.services.idempotency import (
    IdempotencyScope,
    begin_idempotent_request,
    record_idempotency_success,
    safe_request_fingerprint,
)

NOW = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(v2_client_request_id_max_length=64, v2_idempotency_ttl_seconds=60)


def request_scope() -> IdempotencyScope:
    return IdempotencyScope(
        actor_key="synthetic_agent:agent_alex",
        route_key="POST /posts",
        target_key="post:create",
        operation_class="create_post",
    )


def session_factory() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(get_settings().database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False), engine


def test_parallel_same_key_same_fingerprint_has_one_side_effect_and_replay_or_inflight(
    db_session: Session,
) -> None:
    del db_session
    SessionLocal, engine = session_factory()
    first_started = Event()
    release_first = Event()
    call_lock = Lock()
    side_effect_calls = 0
    fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic concurrent idempotent post."},
        allowed_fields={"text"},
    )

    def worker(name: str) -> tuple[str, int | None, dict | None]:
        nonlocal side_effect_calls
        with SessionLocal() as session:
            decision = begin_idempotent_request(
                session,
                request_scope(),
                "parallel-001",
                fingerprint,
                settings=settings(),
                now=NOW,
            )
            if decision.outcome != "started":
                return decision.outcome, decision.status_code, decision.response_json

            first_started.set()
            if name == "first":
                release_first.wait(timeout=5)

            with call_lock:
                side_effect_calls += 1
            record_idempotency_success(
                session,
                decision.record_id,
                status_code=201,
                response_json={"id": "post_parallel_result", "text": "Synthetic result."},
                result_reference="post:post_parallel_result",
            )
            return "completed", 201, {"id": "post_parallel_result", "text": "Synthetic result."}

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(worker, "first")
        assert first_started.wait(timeout=5)
        second_future = executor.submit(worker, "second")
        second_result = second_future.result(timeout=5)
        release_first.set()
        first_result = first_future.result(timeout=5)

    assert first_result[0] == "completed"
    assert second_result[0] in {"in_flight", "replay"}
    assert side_effect_calls == 1

    with SessionLocal() as session:
        retry = begin_idempotent_request(
            session,
            request_scope(),
            "parallel-001",
            fingerprint,
            settings=settings(),
            now=NOW,
        )
        assert retry.outcome == "replay"
        assert retry.status_code == 201
        assert retry.response_json == {"id": "post_parallel_result", "text": "Synthetic result."}
        assert session.scalar(select(func.count(IdempotencyRecord.id))) == 1

    engine.dispose()


def test_conflicting_parallel_fingerprint_returns_conflict_without_second_side_effect(
    db_session: Session,
) -> None:
    del db_session
    SessionLocal, engine = session_factory()
    first_fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic first concurrent post."},
        allowed_fields={"text"},
    )
    conflicting_fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic conflicting concurrent post."},
        allowed_fields={"text"},
    )

    with SessionLocal() as first_session:
        first = begin_idempotent_request(
            first_session,
            request_scope(),
            "parallel-conflict-001",
            first_fingerprint,
            settings=settings(),
            now=NOW,
        )
        assert first.outcome == "started"

    with SessionLocal() as second_session:
        conflict = begin_idempotent_request(
            second_session,
            request_scope(),
            "parallel-conflict-001",
            conflicting_fingerprint,
            settings=settings(),
            now=NOW,
        )
        assert conflict.outcome == "conflict"
        assert conflict.status_code == 409

    with SessionLocal() as first_session:
        record_idempotency_success(
            first_session,
            first.record_id,
            status_code=201,
            response_json={"id": "post_conflict_winner", "text": "Synthetic winner."},
            result_reference="post:post_conflict_winner",
        )

    with SessionLocal() as session:
        assert session.scalar(select(func.count(IdempotencyRecord.id))) == 1

    engine.dispose()
