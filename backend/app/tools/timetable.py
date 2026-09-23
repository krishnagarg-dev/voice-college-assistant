from app.tools.base import EmptyInput, ToolResult, ToolSource, unavailable_result

TOOL_NAME = "get_timetable"
SOURCE = ToolSource(name="KIET timetable service")


def provide_timetable(_: EmptyInput) -> ToolResult:
    """No student-specific timetable provider is connected in this prototype."""
    return unavailable_result(
        TOOL_NAME, SOURCE,
        "No verified public official KIET timetable source is connected. Student-specific timetable access is unavailable.",
    )
