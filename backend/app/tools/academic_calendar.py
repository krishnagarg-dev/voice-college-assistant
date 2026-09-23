from app.tools.base import EmptyInput, ToolResult, ToolSource
from app.tools.official_site import fetch_page

TOOL_NAME = "get_academic_calendar"
SOURCE = ToolSource(
    name="KIET Academic Calendar",
    url="https://www.kiet.edu/academics/academic-calendar/",
)


def provide_academic_calendar(_: EmptyInput) -> ToolResult:
    """Check official HTML; don't infer or construct an unverified PDF URL."""
    _, _, retrieved_at = fetch_page(SOURCE.url)
    return ToolResult(
        tool=TOOL_NAME, success=False, items=[], source=SOURCE,
        retrieved_at=retrieved_at,
        error="The official academic calendar page lists calendar categories but exposes no directly verifiable public calendar document or dated schedule.",
    )
