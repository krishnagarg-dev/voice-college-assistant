"""Central discovery, input validation and execution for assistant tools."""

from app.tools.academic_calendar import SOURCE as CALENDAR_SOURCE
from app.tools.academic_calendar import provide_academic_calendar
from app.tools.base import EmptyInput, ToolDefinition, ToolResult
from app.tools.events import SOURCE as EVENTS_SOURCE
from app.tools.events import provide_upcoming_events
from app.tools.notices import SOURCE as NOTICES_SOURCE
from app.tools.notices import provide_latest_notices
from app.tools.timetable import SOURCE as TIMETABLE_SOURCE
from app.tools.timetable import provide_timetable

TOOLS: dict[str, ToolDefinition] = {
    "get_latest_notices": ToolDefinition(
        name="get_latest_notices",
        description="Retrieve current official KIET circulars and notices.",
        input_model=EmptyInput,
        provider=provide_latest_notices,
        source=NOTICES_SOURCE,
    ),
    "get_upcoming_events": ToolDefinition(
        name="get_upcoming_events",
        description="Retrieve upcoming official KIET events.",
        input_model=EmptyInput,
        provider=provide_upcoming_events,
        source=EVENTS_SOURCE,
    ),
    "get_academic_calendar": ToolDefinition(
        name="get_academic_calendar",
        description="Retrieve the current official KIET academic calendar.",
        input_model=EmptyInput,
        provider=provide_academic_calendar,
        source=CALENDAR_SOURCE,
    ),
    "get_timetable": ToolDefinition(
        name="get_timetable",
        description="Retrieve a timetable when an approved timetable provider is connected.",
        input_model=EmptyInput,
        provider=provide_timetable,
        source=TIMETABLE_SOURCE,
    ),
}


def list_tools() -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_model.model_json_schema(),
        }
        for tool in TOOLS.values()
    ]


def get_tool(name: str) -> ToolDefinition | None:
    return TOOLS.get(name)


def execute_tool(name: str, arguments: dict | None = None) -> ToolResult:
    tool = get_tool(name)
    if tool is None:
        from datetime import datetime, timezone

        return ToolResult(
            tool=name,
            success=False,
            items=[],
            source=None,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            error="Unknown tool.",
        )
    return tool.execute(arguments)
