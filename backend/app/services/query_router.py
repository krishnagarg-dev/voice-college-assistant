"""Small deterministic router that keeps dynamic requests off static RAG."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingDecision:
    mode: str
    tools: tuple[str, ...] = ()
    use_rag: bool = True


_DYNAMIC_INTENTS = (
    ("get_latest_notices", ("notice", "circular", "announcement")),
    ("get_upcoming_events", ("event", "upcoming event", "coming up")),
    ("get_academic_calendar", ("academic calendar",)),
    ("get_timetable", ("timetable", "time table", "class schedule")),
)
_STABLE_INTENTS = (
    "policy", "policies", "rule", "rules", "regulation", "regulations",
    "program", "programs", "syllabus", "admission", "scholarship",
    "handbook", "what is kiet", "about kiet", "fee structure",
)


def route_query(query: str) -> RoutingDecision:
    normalized = " ".join(query.casefold().split())
    selected = []
    for tool_name, phrases in _DYNAMIC_INTENTS:
        if any(phrase in normalized for phrase in phrases):
            selected.append(tool_name)
    if not selected:
        return RoutingDecision(mode="rag", use_rag=True)

    wants_stable_context = any(phrase in normalized for phrase in _STABLE_INTENTS)
    # Mixed current and stable questions use both paths; repeated tool intents can
    # execute together while avoiding an unnecessary RAG call.
    return RoutingDecision(
        mode="hybrid" if wants_stable_context else "tool",
        tools=tuple(selected),
        use_rag=wants_stable_context,
    )
