import os
import unittest
from unittest.mock import MagicMock, patch

from app.config.settings import settings
from app.services.llm_service import (
    LLMConfigurationError,
    LLMServiceError,
    _safe_provider_diagnostic,
    generate_answer,
)


class GeminiConfigurationTests(unittest.TestCase):
    def test_settings_read_gemini_values_from_environment(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real", "GEMINI_MODEL": "test-model"}):
            self.assertTrue(settings.gemini_api_key)
            self.assertEqual(settings.gemini_model, "test-model")
            self.assertFalse(hasattr(settings, "openai_api_key"))

    def test_unset_api_key_has_actionable_configuration_error(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(LLMConfigurationError, "GEMINI_API_KEY"):
                generate_answer("question", "context")


class GeminiGenerationTests(unittest.TestCase):
    @patch("app.services.llm_service.genai.Client")
    def test_gemini_receives_grounded_context_and_system_instruction(self, client_class):
        response = MagicMock()
        response.text = "Grounded response"
        client_class.return_value.models.generate_content.return_value = response
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real", "GEMINI_MODEL": "gemini-test-model"}):
            answer = generate_answer("What programs?", "Official KIET program context")
        self.assertEqual(answer, "Grounded response")
        kwargs = client_class.return_value.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-test-model")
        self.assertIn("Official KIET program context", kwargs["contents"])
        self.assertIn("Do not invent facts", kwargs["config"].system_instruction)
        self.assertIn("Do not begin with meta-introductions", kwargs["config"].system_instruction)
        self.assertEqual(kwargs["config"].temperature, 0.1)

    @patch("app.services.llm_service.genai.Client")
    def test_provider_errors_are_sanitized(self, client_class):
        client_class.return_value.models.generate_content.side_effect = RuntimeError("sensitive provider details")
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real"}):
            with self.assertRaises(LLMServiceError) as raised:
                generate_answer("question", "context")
        self.assertNotIn("sensitive provider details", str(raised.exception))
        self.assertNotIn("test-key-not-real", str(raised.exception))

    def test_provider_diagnostics_redact_credentials_and_bound_message(self):
        class ProviderError(Exception):
            code = 403
            status = "PERMISSION_DENIED"
            message = "API key=secret-value Authorization: Bearer hidden-token " + ("x" * 700)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-value"}):
            http_status, error_code, message = _safe_provider_diagnostic(ProviderError())
        self.assertEqual(http_status, "403")
        self.assertEqual(error_code, "PERMISSION_DENIED")
        self.assertNotIn("secret-value", message)
        self.assertNotIn("hidden-token", message)
        self.assertLessEqual(len(message), 500)


if __name__ == "__main__":
    unittest.main()
