FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true

RUN poetry install --no-root --without dev

COPY src src
COPY fixtures fixtures

FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/fixtures /app/fixtures

RUN chown -R appuser:appuser /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8090
CMD ["uvicorn", "src.app:app", "--host","0.0.0.0","--port", "8090"]