import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.rag.pipeline import LLMConfigurationError, LLMServiceError
from app.services.chat_service import create_chat_response
from app.tools.base import ToolSource
from app.tools.registry import list_tools

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        return cleaned


class SourceReference(BaseModel):
    document: str
    page: int | None = None
    url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    response_type: Literal["answer", "no_information"] = "answer"
    escalation_category: Literal["admissions", "general"] | None = None
    tool_sources: list[ToolSource] = Field(default_factory=list)


@router.get("/tools")
def available_tools() -> list[dict]:
    """Expose the safe, read-only tool catalog and input schemas."""
    return list_tools()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return ChatResponse(**create_chat_response(request.message))
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="The KIET assistant is temporarily unavailable. Please try again later.",
        ) from exc
    except LLMServiceError as exc:
        logging.getLogger(__name__).exception("LLM answer generation failed")
        raise HTTPException(
            status_code=503,
            detail="The KIET assistant is temporarily unavailable. Please try again later.",
        ) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("RAG chat request failed")
        raise HTTPException(
            status_code=503,
            detail="The KIET information service is temporarily unavailable. Please try again later.",
        ) from exc
