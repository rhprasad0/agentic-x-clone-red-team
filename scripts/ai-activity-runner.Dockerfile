FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN adduser -D -u 10001 -s /sbin/nologin runner

WORKDIR /workspace

COPY scripts/ai_activity_runner.py ./scripts/ai_activity_runner.py
COPY scripts/fake_openai_compatible_llm.py ./scripts/fake_openai_compatible_llm.py
COPY scripts/ai_activity_runner_lib ./scripts/ai_activity_runner_lib

RUN chown -R runner:runner /workspace

USER runner

ENTRYPOINT ["python", "scripts/ai_activity_runner.py"]
CMD ["--help"]
