import logging
import re

from app.rag.pipeline import answer_question
from app.services.query_router import route_query
from app.tools.base import ToolResult
from app.tools.registry import execute_tool

logger = logging.getLogger(__name__)
_ADMISSION_ESCALATION_TERMS = re.compile(
    r"\b(admissions?|apply|applying|application|eligibility|entrance exams?|counsell?ors?|counsell?ing)\b",
    re.IGNORECASE,
)


def _format_tool_results(results: list[ToolResult]) -> str:
    lines = []
    for result in results:
        if not result.success:
            lines.append(result.error or "Tool data is currently unavailable.")
            continue
        if not result.items:
            lines.append(result.error or "The official source returned no records.")
            continue
        for item in result.items:
            detail = " — ".join(value for value in (item.date, item.description, item.location) if value)
            lines.append(f"{item.title}{': ' + detail if detail else ''}")
    return "\n".join(lines) or "Tool data is currently unavailable."


def create_chat_response(message: str) -> dict:
    """Route current requests to tools and stable institutional queries to RAG."""
    decision = route_query(message)
    logger.info("chat route mode=%s tools=%s query_chars=%d", decision.mode, decision.tools, len(message))

    rag_response = None
    if decision.use_rag:
        rag_response = answer_question(message)
        logger.info("rag retrieval citations=%d", len(rag_response.get("sources", [])))

    tool_results = [execute_tool(name, {}) for name in decision.tools]
    for result in tool_results:
        logger.info("tool execution name=%s success=%s items=%d", result.tool, result.success, len(result.items))

    if rag_response is not None:
        answer = rag_response["answer"]
        response_type = rag_response.get("response_type", "answer")
        if tool_results:
            tool_answer = _format_tool_results(tool_results)
            if response_type == "no_information":
                answer = tool_answer
            else:
                answer = f"{answer}\n\nCurrent information:\n{tool_answer}"
            # A tool-backed hybrid result must not be presented as a RAG no-context result.
            response_type = "answer"
        rag_sources = rag_response.get("sources", [])
    else:
        answer = _format_tool_results(tool_results)
        rag_sources = []
        response_type = "answer"

    escalation_category = None
    if response_type == "no_information":
        escalation_category = "admissions" if _ADMISSION_ESCALATION_TERMS.search(message) else "general"

    tool_sources = []
    seen_sources = set()
    for result in tool_results:
        source = result.source
        if source and (source.name, source.url) not in seen_sources:
            tool_sources.append(source.model_dump(exclude_none=True))
            seen_sources.add((source.name, source.url))

    response = {
        "answer": answer,
        "response_type": response_type,
        "escalation_category": escalation_category,
        "source": decision.mode,
        "sources": rag_sources,
        "mode": decision.mode,
        "tool_used": list(decision.tools),
        "tool_sources": tool_sources,
        "tool_results": [result.model_dump(exclude_none=True) for result in tool_results],
    }
    logger.info("chat complete mode=%s answer_chars=%d", decision.mode, len(answer))
    return response
