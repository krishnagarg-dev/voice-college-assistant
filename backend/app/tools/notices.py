from app.tools.base import EmptyInput, ToolResult, ToolSource
from app.tools.official_site import fetch_page
from app.tools.page_parser import extract_records

TOOL_NAME = "get_latest_notices"
SOURCE = ToolSource(
    name="KIET Circulars & Notices",
    url="https://www.kiet.edu/academics/circulars-notices/",
)


def provide_latest_notices(_: EmptyInput) -> ToolResult:
    """Fetch and extract visible notice cards from the official KIET page."""
    html, final_url, retrieved_at = fetch_page(SOURCE.url)
    items = extract_records(html, final_url)
    return ToolResult(
        tool=TOOL_NAME, success=True, items=items, source=SOURCE,
        retrieved_at=retrieved_at,
        error=None if items else "The official notices page loaded, but exposes no notice records to this public page fetch.",
    )
