import logging
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from pydantic import BaseModel, Field

from src.graph.answerer import synthesize_answer
from src.graph.planner import plan_request
from src.graph.retriever import retrieve_docs
from src.sse import sse_event

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    plan: dict[str, Any] = Field(default_factory=dict)
    retrieved: list[dict[str, Any]] = Field(default_factory=list)
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    top_ids: list[str] = Field(default_factory=list)


graph = StateGraph(AgentState)


def plan_node(state: AgentState):
    logger.debug(f"plan node: {state}")
    plan = plan_request(state.messages[-1].content, {}, 5)
    logger.debug(f"plan node plan: {plan}")
    return {"plan": plan}


def retrieve_node(state: AgentState):
    logger.debug(f"retrieve node: {state}")
    return retrieve_docs(state.plan)


def synthesize_node(state: AgentState):
    # Build system+context prompt with doc snippets; ask for inline [n] refs.
    # Stream via llm.astream and forward deltas; also accumulate full text + compute citations.
    ...
    answer, top_ids = synthesize_answer(state.messages[-1].content, state.retrieved)
    logger.debug(f"synthesized answer: {answer}")
    return {"messages": AIMessage(answer), "top_ids": top_ids}


graph.add_node("plan", plan_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("synthesize", synthesize_node)

graph.add_edge(START, "plan")
graph.add_edge("plan", "retrieve")
graph.add_edge("retrieve", "synthesize")
graph.add_edge("synthesize", END)
checkpointer = InMemorySaver()

agent_app = graph.compile(checkpointer=checkpointer)


def invoke(req: Any):
    config: RunnableConfig = {"configurable": {"thread_id": req.conversationId}}
    for _channel, payload in agent_app.stream(
        {"messages": [HumanMessage(getattr(req, "message", ""))]}, config, stream_mode=["messages"]
    ):
        message_obj, _meta = payload
        logger.debug(f"received message: {message_obj}")
        content = message_obj.content
        if isinstance(content, str) and content:
            yield sse_event("token", {"content": content})
    yield sse_event("done", {})
