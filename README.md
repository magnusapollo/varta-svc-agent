# varta-svc-agent (Mock-First)

Agent service for chat + RAG over **site-only data**. Streams SSE tokens and returns citations.
No production ops: run locally with one command. Pluggable LLM provider (local stub or OpenAI).

## Quick start (Poetry)

```bash
# Install deps
poetry install

# Configure env
cp .env.example .env
# If using OpenAI provider, set OPENAI_API_KEY in .env and ensure MODEL_NAME=openai:gpt-5

# Run dev server on :8090
poetry run uvicorn src.app:app --reload --port 8090
```

### Endpoints

- `GET /health` → `{ "status": "ok" }`
- `POST /agent/v1/retrieve/test`
- `POST /agent/v1/chat/stream` (SSE: events `token`, `citations`, `done`)

### Toggle mocks

Edit `.env`:

```
USE_MOCKS=true
CORE_API_BASE=http://localhost:8080/api/v1
MODEL_NAME=stub-local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MAX_TOKENS=800
TEMPERATURE=0.3
```

- `USE_MOCKS=true`: load fixtures from `./fixtures`, build an in-memory vector store (no FAISS required).
- `USE_MOCKS=false`: keyword retrieval goes to Core API (`/search`), item resolution via `/items/{slug}`.
  Vector store remains local & read-only (optional).

### Build / refresh local vector index

```bash
python scripts/build_index.py
```

### Tests

```bash
pytest -q
```

### Project layout

```
varta-svc-agent/
├─ pyproject.toml
├─ requirements.txt
├─ .env.example
├─ fixtures/
├─ src/
│  ├─ app.py
│  ├─ sse.py
│  ├─ config.py
│  ├─ types.py
│  ├─ graph/
│  │  ├─ planner.py
│  │  ├─ retriever.py
│  │  ├─ answerer.py
│  │  └─ guardrails.py
│  ├─ retrieval/
│  │  ├─ client_coreapi.py
│  │  ├─ store_vector.py
│  │  └─ hybrid.py
│  ├─ llm/
│  │  ├─ provider.py
│  │  └─ stub_local.py
│  └─ utils/
│     ├─ time.py
│     └─ text.py
└─ tests/
```

## Acceptance checklist

- `uvicorn src.app:app --reload --port 8090` starts.
- `POST /agent/v1/chat/stream` streams tokens and `citations` then `done`.
- `POST /agent/v1/retrieve/test` returns stable top‑k from fixtures.
- Switch `USE_MOCKS=false` to hit Core API contracts (stubbed client).

