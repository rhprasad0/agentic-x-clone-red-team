FROM python:3.12-alpine AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY apps/backend/pyproject.toml ./
COPY apps/backend/app ./app

RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip \
    && /opt/venv/bin/python -m pip install .

FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN adduser -D -u 10001 -s /sbin/nologin appuser

WORKDIR /workspace/apps/backend

COPY --from=builder /opt/venv /opt/venv
COPY apps/backend/alembic.ini ./alembic.ini
COPY apps/backend/alembic ./alembic
COPY apps/backend/app ./app
COPY fixtures/used_car_world /workspace/fixtures/used_car_world

RUN chown -R appuser:appuser /workspace /opt/venv

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read(); sys.exit(0)"

CMD ["sh", "-c", "alembic -c alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
