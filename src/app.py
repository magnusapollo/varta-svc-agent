from collections.abc import AsyncGenerator
import logging

from fastapi import Body, FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import settings
from .graph.graph import invoke
from .types import ChatRequest

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Custom format string
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


app = FastAPI(title="varta-svc-agent", version="0.1.0")


class Health(BaseModel):
    status: str = "ok"


@app.get("/health", response_model=Health)
async def health():
    return Health()


@app.post("/agent/v1/chat/stream")
async def chat_stream(req: ChatRequest = Body(...)):
    async def event_gen() -> AsyncGenerator[bytes, None]:
       for chunk in invoke(req):
            yield chunk

       """
       # citations event
       yield sse_event("citations", {"citations": final_payload["citations"]})
        
       # done event
       yield sse_event(
           "done", {"usage": {"input": len(req.message), "output": len(final_payload["answer"])}}
       )
       """

    return StreamingResponse(event_gen(), media_type="text/event-stream")
