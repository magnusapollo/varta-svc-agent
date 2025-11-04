# varta-svc-agent

Agent service for chat + RAG over **site-only data**. Streams SSE tokens and returns citations.
No production ops: run locally with one command. Pluggable LLM provider (local stub or OpenAI).

## 🧩 Local Setup & Development
### Prerequisites
* Python 3.11 – 3.13 (recommended 3.12)
```bash
brew install python@3.12
```
* Poetry (for dependency + environment management)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```
Optional: oh-my-zsh virtualenv plugin (no special config needed).
### 1️⃣ Install dependencies
If you already have Python 3.12 installed, Poetry will automatically use it — no need for poetry env use.
poetry install
If you want to include the embedding stack (torch + sentence-transformers):
poetry install --with embeddings
This may take several minutes because it downloads pre-built PyTorch wheels.
### 2️⃣ Environment configuration
```bash
cp .env.example .env
```
Then open .env and set your model preference:
```env
# Local stub
MODEL_NAME=stub-local

# Or OpenAI GPT-5 (requires API key)
MODEL_NAME=openai:gpt-5
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```
### 3️⃣ Run the development server
No need to “activate” the virtual environment — just use poetry run:
```bash
poetry run uvicorn src.app:app --reload --port 8090
```
Visit http://localhost:8090/health → should return:
```json
{"status": "ok"}
```
### 4️⃣ Run tests
```bash
poetry run pytest
```
### 5️⃣ (Optionally) enter the venv manually
If you prefer a manual shell (for Oh-My-Zsh + virtualenv plugin):
```bash 
source $(poetry env info --path)/bin/activate
# or simply:
source .venv/bin/activate
```



## Build / refresh local vector index

```bash
python scripts/build_index.py
```

