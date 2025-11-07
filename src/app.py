from collections.abc import AsyncGenerator
import logging

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import settings
from .graph.answerer import synthesize_answer
from .graph.guardrails import enforce_citations
from .graph.planner import plan_request
from .graph.retriever import retrieve_docs
from .llm.provider import choose_model
from .sse import sse_event
from .types import ChatRequest, RetrieveRequest

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Custom format string
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


app = FastAPI(title="varta-svc-agent", version="0.1.0")
model = choose_model(settings.model_name)


class Health(BaseModel):
    status: str = "ok"


@app.get("/health", response_model=Health)
async def health():
    return Health()


@app.post("/agent/v1/retrieve/test")
async def retrieve_test(req: RetrieveRequest = Body(...)):
    plan = plan_request(req.query, req.filters, req.k)
    results = await retrieve_docs(plan)
    return JSONResponse(content={"results": results})


@app.post("/agent/v1/chat/stream")
async def chat_stream(req: ChatRequest = Body(...)):
    async def event_gen() -> AsyncGenerator[bytes, None]:
        plan = plan_request(req.message, req.filters, settings.retrieve_k)
        results = await retrieve_docs(plan)
        answer, citation_ids = synthesize_answer(
            req.message,
            results,
            model=model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

        final_payload = enforce_citations(
            answer, results, citation_ids, min_citations=settings.min_citations
        )

        # stream tokens
        for chunk in final_payload["answer_stream"]:
            yield sse_event("token", {"content": chunk})

        # citations event
        yield sse_event("citations", {"citations": final_payload["citations"]})

        # done event
        yield sse_event(
            "done", {"usage": {"input": len(req.message), "output": len(final_payload["answer"])}}
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")
