import unittest
from unittest.mock import patch

from app.routes.chat import ChatResponse
from app.services.chat_service import create_chat_response
from app.services.query_router import route_query
from app.tools.base import ToolResult, ToolSource
from app.tools.registry import execute_tool, list_tools


class QueryRoutingTests(unittest.TestCase):
    def test_stable_questions_use_rag(self):
        for question in (
            "What is KIET?",
            "What are KIET rules?",
            "What programs does KIET offer?",
        ):
            with self.subTest(question=question):
                decision = route_query(question)
                self.assertEqual(decision.mode, "rag")
                self.assertTrue(decision.use_rag)
                self.assertEqual(decision.tools, ())

    def test_dynamic_questions_select_expected_tool(self):
        cases = {
            "What are the latest notices?": "get_latest_notices",
            "What events are coming up?": "get_upcoming_events",
            "What is the current academic calendar?": "get_academic_calendar",
            "What is my current timetable?": "get_timetable",
        }
        for question, expected_tool in cases.items():
            with self.subTest(question=question):
                decision = route_query(question)
                self.assertEqual(decision.mode, "tool")
                self.assertFalse(decision.use_rag)
                self.assertEqual(decision.tools, (expected_tool,))

    def test_mixed_question_selects_hybrid(self):
        decision = route_query("What is the scholarship policy and are there latest notices?")
        self.assertEqual(decision.mode, "hybrid")
        self.assertTrue(decision.use_rag)
        self.assertEqual(decision.tools, ("get_latest_notices",))


class ToolRegistryTests(unittest.TestCase):
    def test_tools_are_discoverable_with_schemas(self):
        tools = list_tools()
        self.assertEqual(len(tools), 4)
        self.assertTrue(all("input_schema" in tool for tool in tools))

    def test_unknown_tool_fails_safely(self):
        result = execute_tool("unknown_tool")
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertEqual(result.error, "Unknown tool.")

    def test_invalid_input_fails_safely(self):
        result = execute_tool("get_latest_notices", {"student_id": "not-accepted"})
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertEqual(result.error, "Invalid input for this tool.")

    @patch("app.tools.notices.fetch_page")
    def test_live_provider_does_not_invent_items_when_page_is_empty(self, fetch):
        fetch.return_value = (
            "<main><h2>Circulars &amp; Notices</h2></main>",
            "https://www.kiet.edu/academics/circulars-notices/",
            "2026-09-24T00:00:00+00:00",
        )
        result = execute_tool("get_latest_notices")
        self.assertTrue(result.success)
        self.assertEqual(result.items, [])
        self.assertIsNotNone(result.source)


class ChatCompatibilityTests(unittest.TestCase):
    @patch("app.services.chat_service.execute_tool")
    def test_tool_failure_response_is_grounded_and_distinguishes_sources(self, execute_tool_mock):
        execute_tool_mock.return_value = ToolResult(
            tool="get_latest_notices",
            success=False,
            items=[],
            source=ToolSource(name="KIET Circulars & Notices", url="https://www.kiet.edu/academics/circulars-notices/"),
            retrieved_at="2026-01-01T00:00:00+00:00",
            error="Tool data is currently unavailable.",
        )
        response = create_chat_response("What are the latest notices?")
        self.assertEqual(response["mode"], "tool")
        self.assertEqual(response["tool_used"], ["get_latest_notices"])
        self.assertEqual(response["sources"], [])
        self.assertEqual(response["tool_sources"][0]["name"], "KIET Circulars & Notices")
        self.assertIn("currently unavailable", response["answer"])

    def test_legacy_response_fields_remain_valid(self):
        response = ChatResponse(answer="Grounded", source="rag", sources=[])
        self.assertEqual(response.response_type, "answer")
        self.assertIsNone(response.escalation_category)
        self.assertEqual(response.tool_sources, [])

    @patch("app.services.chat_service.answer_question")
    def test_rag_response_keeps_legacy_fields(self, answer_question_mock):
        answer_question_mock.return_value = {
            "answer": "KIET answer",
            "source": "rag",
            "sources": [{"document": "KIET Overview", "page": None, "url": "https://www.kiet.edu/about/Overview/"}],
        }
        response = create_chat_response("What is KIET?")
        self.assertEqual(response["answer"], "KIET answer")
        self.assertEqual(response["sources"][0]["document"], "KIET Overview")
        self.assertEqual(response["tool_used"], [])

    @patch("app.services.chat_service.answer_question")
    @patch("app.services.chat_service.execute_tool")
    def test_hybrid_response_keeps_rag_and_tool_sources_separate(self, execute_tool_mock, answer_question_mock):
        answer_question_mock.return_value = {
            "answer": "KIET policy answer",
            "source": "rag",
            "sources": [{"document": "KIET Student Handbook", "page": 2}],
        }
        execute_tool_mock.return_value = ToolResult(
            tool="get_latest_notices",
            success=False,
            items=[],
            source=ToolSource(name="KIET Circulars & Notices", url="https://www.kiet.edu/academics/circulars-notices/"),
            retrieved_at="2026-01-01T00:00:00+00:00",
            error="Tool data is currently unavailable.",
        )
        response = create_chat_response("What is the scholarship policy and are there latest notices?")
        self.assertEqual(response["sources"][0]["document"], "KIET Student Handbook")
        self.assertEqual(response["tool_sources"][0]["name"], "KIET Circulars & Notices")
        self.assertIn("KIET policy answer", response["answer"])
        self.assertIn("currently unavailable", response["answer"])


if __name__ == "__main__":
    unittest.main()
