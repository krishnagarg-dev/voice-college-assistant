import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.rag.pipeline import answer_question
from app.services.llm_service import LLMServiceError
from app.tools.base import ToolItem, ToolResult, ToolSource


class ApiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_tool_catalog_endpoints(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        response = self.client.get("/api/tools")
        self.assertEqual(response.status_code, 200)
        names = {tool["name"] for tool in response.json()}
        self.assertEqual(names, {"get_latest_notices", "get_upcoming_events", "get_academic_calendar", "get_timetable"})

    @patch("app.main.ensure_knowledge_index", side_effect=RuntimeError("temporary source outage"))
    def test_health_starts_even_if_rag_initialization_is_unavailable(self, initialize_index):
        with TestClient(app) as client:
            response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        initialize_index.assert_called_once_with()

    @patch("app.rag.pipeline.retrieve", return_value=[])
    def test_rag_no_context_returns_structured_no_information(self, _retrieve):
        result = answer_question("Question with no indexed source")
        self.assertEqual(result["response_type"], "no_information")
        self.assertEqual(result["sources"], [])

    @patch("app.services.chat_service.execute_tool")
    def test_chat_tool_response_preserves_fields_and_citation(self, execute_tool):
        execute_tool.return_value = ToolResult(
            tool="get_latest_notices", success=True,
            items=[ToolItem(title="Official circular", date="24/09/2026", document_url="https://www.kiet.edu/docs/circular.pdf")],
            source=ToolSource(name="KIET Circulars & Notices", url="https://www.kiet.edu/academics/circulars-notices/"),
            retrieved_at="2026-09-24T00:00:00+00:00",
        )
        response = self.client.post("/api/chat", json={"message": "What are the latest notices?"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["response_type"], "answer")
        self.assertIsNone(body["escalation_category"])
        self.assertEqual(body["tool_sources"][0]["url"], "https://www.kiet.edu/academics/circulars-notices/")
        self.assertNotIn("tool_results", body)
        self.assertNotIn("tool_used", body)
        self.assertNotIn("mode", body)

    @patch("app.services.chat_service.answer_question")
    def test_rag_question_keeps_existing_answer_and_citations(self, answer_question):
        answer_question.return_value = {
            "answer": "KIET grounded answer", "source": "rag",
            "sources": [{"document": "Official KIET Programs", "url": "https://www.kiet.edu/programs/"}],
        }
        response = self.client.post("/api/chat", json={"message": "What programs does KIET offer?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "KIET grounded answer")
        self.assertEqual(response.json()["sources"][0]["document"], "Official KIET Programs")
        self.assertNotIn("category", response.json()["sources"][0])
        self.assertNotIn("source_type", response.json()["sources"][0])
        self.assertNotIn("mode", response.json())
        self.assertNotIn("tool_used", response.json())
        self.assertNotIn("tool_results", response.json())
        self.assertEqual(response.json()["response_type"], "answer")
        self.assertIsNone(response.json()["escalation_category"])

    @patch("app.services.chat_service.answer_question")
    def test_no_information_response_is_structured_and_deterministically_categorized(self, answer_question):
        answer_question.return_value = {
            "answer": "I don't have enough verified information to answer that accurately.",
            "source": "rag", "sources": [], "response_type": "no_information",
        }
        for question, expected_category in (
            ("What are KIET admission requirements?", "admissions"),
            ("What is the capital of Narnia?", "general"),
        ):
            with self.subTest(question=question):
                response = self.client.post("/api/chat", json={"message": question})
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["response_type"], "no_information")
                self.assertEqual(body["escalation_category"], expected_category)
                self.assertEqual(body["sources"], [])

    @patch("app.services.chat_service.answer_question", side_effect=LLMServiceError("service unavailable"))
    def test_backend_error_does_not_return_no_information_metadata(self, _answer_question):
        response = self.client.post("/api/chat", json={"message": "What is MCA?"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("GEMINI_API_KEY", response.json()["detail"])
        self.assertNotIn("service unavailable", response.json()["detail"])
        self.assertNotIn("response_type", response.json())

    @patch("app.services.chat_service.execute_tool")
    @patch("app.services.chat_service.answer_question")
    def test_hybrid_response_keeps_rag_and_tool_sources(self, answer_question, execute_tool):
        answer_question.return_value = {"answer": "Official policy answer", "source": "rag", "sources": [{"document": "KIET rules"}]}
        execute_tool.return_value = ToolResult(
            tool="get_latest_notices", success=False, items=[],
            source=ToolSource(name="KIET Circulars & Notices", url="https://www.kiet.edu/academics/circulars-notices/"),
            retrieved_at="2026-09-24T00:00:00+00:00", error="No public notice records were exposed.",
        )
        response = self.client.post("/api/chat", json={"message": "What is the rules policy and latest notices?"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["response_type"], "answer")
        self.assertNotIn("tool_results", body)
        self.assertIsNone(body["escalation_category"])
        self.assertEqual(body["sources"][0]["document"], "KIET rules")
        self.assertEqual(body["tool_sources"][0]["name"], "KIET Circulars & Notices")
        self.assertIn("No public notice records", body["answer"])


if __name__ == "__main__":
    unittest.main()
