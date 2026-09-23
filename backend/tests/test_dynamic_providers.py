import unittest
from unittest.mock import patch

from app.tools.academic_calendar import provide_academic_calendar
from app.tools.base import EmptyInput
from app.tools.events import provide_upcoming_events
from app.tools.notices import provide_latest_notices
from app.tools.page_parser import extract_records
from app.tools.registry import execute_tool
from app.tools.timetable import provide_timetable


class DynamicProviderTests(unittest.TestCase):
    def test_notice_card_extraction_is_structured_and_domain_limited(self):
        html = '''<main><article class="notice-card"><h3>Example Circular</h3>
            <time>12/09/2026</time><a href="/documents/circular.pdf">PDF</a></article>
            <article class="notice-card"><h3>External</h3><a href="https://example.com/a.pdf">PDF</a></article></main>'''
        items = extract_records(html, "https://www.kiet.edu/academics/circulars-notices/")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Example Circular")
        self.assertEqual(items[0].date, "12/09/2026")
        self.assertEqual(items[0].document_url, "https://www.kiet.edu/documents/circular.pdf")
        self.assertIsNone(items[1].url)
        self.assertIsNone(items[1].document_url)

    @patch("app.tools.notices.fetch_page")
    def test_notices_preserve_source_freshness_and_empty_behavior(self, fetch):
        fetch.return_value = ("<main><h2>Circulars &amp; Notices</h2></main>", "https://www.kiet.edu/academics/circulars-notices/", "2026-09-24T00:00:00+00:00")
        result = provide_latest_notices(EmptyInput())
        self.assertTrue(result.success)
        self.assertEqual(result.items, [])
        self.assertEqual(result.source.url, "https://www.kiet.edu/academics/circulars-notices/")
        self.assertEqual(result.retrieved_at, "2026-09-24T00:00:00+00:00")
        self.assertIn("exposes no notice records", result.error)

    @patch("app.tools.events.fetch_page")
    def test_events_only_return_future_dated_cards(self, fetch):
        fetch.return_value = ('''<main>
          <article class="event-card"><h3>Past Event</h3><time>01/01/2020</time></article>
          <article class="event-card"><h3>Future Event</h3><time>December 31, 2099</time></article>
        </main>''', "https://www.kiet.edu/events/events/", "2026-09-24T00:00:00+00:00")
        result = provide_upcoming_events(EmptyInput())
        self.assertTrue(result.success)
        self.assertEqual([item.title for item in result.items], ["Future Event"])
        self.assertEqual(result.source.url, "https://www.kiet.edu/events/events/")
        self.assertTrue(result.retrieved_at)

    @patch("app.tools.events.fetch_page")
    def test_events_without_dates_are_unavailable(self, fetch):
        fetch.return_value = ("<main><h3>Smart India Hackathon 2026</h3></main>", "https://www.kiet.edu/events/events/", "2026-09-24T00:00:00+00:00")
        result = provide_upcoming_events(EmptyInput())
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertIn("machine-readable dates", result.error)

    @patch("app.tools.academic_calendar.fetch_page")
    def test_calendar_fails_safely_without_public_document(self, fetch):
        fetch.return_value = ("<main>Academic Calendar 2026-27</main>", "https://www.kiet.edu/academics/academic-calendar/", "2026-09-24T00:00:00+00:00")
        result = provide_academic_calendar(EmptyInput())
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertEqual(result.source.url, "https://www.kiet.edu/academics/academic-calendar/")
        self.assertIn("no directly verifiable", result.error)

    def test_fetch_or_extraction_failures_do_not_leak_technical_errors(self):
        with patch("app.tools.notices.fetch_page", side_effect=OSError("network internals")), self.assertLogs("app.tools.base", level="ERROR"):
            result = execute_tool("get_latest_notices")
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertNotIn("network internals", result.error)
        self.assertIn("kiet.edu", result.source.url)

    def test_timetable_remains_unavailable_with_source_reason(self):
        result = provide_timetable(EmptyInput())
        self.assertFalse(result.success)
        self.assertEqual(result.items, [])
        self.assertIn("No verified public official KIET timetable", result.error)


if __name__ == "__main__":
    unittest.main()
