FROM python:3.12-slim as builder
WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true

RUN poetry install --no-root --without dev

COPY src src
COPY fixtures fixtures

FROM python:3.12-slim as production

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/fixtures /app/fixtures

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8090
CMD ["uvicorn", "src.app:app", "--host","0.0.0.0","--port", "8090"]