from datetime import date

from app.tools.base import EmptyInput, ToolResult, ToolSource
from app.tools.official_site import fetch_page
from app.tools.page_parser import extract_records, parse_date

TOOL_NAME = "get_upcoming_events"
SOURCE = ToolSource(
    name="KIET Events",
    url="https://www.kiet.edu/events/events/",
)


def provide_upcoming_events(_: EmptyInput) -> ToolResult:
    """Fetch events and include only records with a verified future date."""
    html, final_url, retrieved_at = fetch_page(SOURCE.url)
    extracted = extract_records(html, final_url)
    upcoming = []
    for item in extracted:
        event_date = parse_date(item.date) if item.date else None
        if event_date and event_date >= date.today():
            upcoming.append(item)
    return ToolResult(
        tool=TOOL_NAME, success=bool(upcoming), items=upcoming, source=SOURCE,
        retrieved_at=retrieved_at,
        error=None if upcoming else "The official events page does not expose machine-readable dates that can verify which events are upcoming.",
    )
