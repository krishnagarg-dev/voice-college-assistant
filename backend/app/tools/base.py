"""Shared structured contract for dynamic information tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Callable, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyInput(ToolInput):
    pass


class ToolSource(BaseModel):
    name: str
    url: str | None = None


class ToolItem(BaseModel):
    title: str
    date: str | None = None
    url: str | None = None
    document_url: str | None = None
    category: str | None = None
    description: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    weekday: str | None = None
    time_slot: str | None = None
    course: str | None = None
    room: str | None = None


class ToolResult(BaseModel):
    tool: str
    success: bool
    items: list[ToolItem] = Field(default_factory=list)
    source: ToolSource | None = None
    retrieved_at: str
    error: str | None = None


def unavailable_result(tool: str, source: ToolSource, error: str | None = None) -> ToolResult:
    return ToolResult(
        tool=tool,
        success=False,
        items=[],
        source=source,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        error=error or "Tool data is currently unavailable. Live KIET data has not been connected yet.",
    )


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: Type[ToolInput]
    provider: Callable[[ToolInput], ToolResult]
    source: ToolSource

    def execute(self, arguments: dict | None = None) -> ToolResult:
        try:
            parsed = self.input_model.model_validate(arguments or {})
        except ValidationError:
            return unavailable_result(self.name, self.source).model_copy(
                update={"error": "Invalid input for this tool."}
            )
        try:
            result = self.provider(parsed)
            if result.tool != self.name:
                raise ValueError("Provider returned a mismatched tool name")
            return result
        except Exception:
            logging.getLogger(__name__).exception("Dynamic tool provider failed: %s", self.name)
            return unavailable_result(
                self.name, self.source,
                "The official KIET source could not be retrieved or safely interpreted right now.",
            )
