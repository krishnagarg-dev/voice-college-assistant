import unittest
from unittest.mock import patch

from app.rag.pipeline import answer_question
from app.rag.retriever import retrieve
from app.rag.web_ingest import load_registry
from app.rag.web_loader import canonicalize_url


class PlacementRegistryTests(unittest.TestCase):
    def test_official_placement_sources_are_registered_with_mca_metadata(self):
        registry = load_registry()
        placement = [entry for entry in registry if entry["category"] == "placements"]
        self.assertEqual(len(placement), 5)
        mca = next(entry for entry in registry if entry.get("programme") == "MCA")
        self.assertEqual(mca["url"], "https://kiet.edu/programs/ksoca/MCA/")
        self.assertEqual(canonicalize_url(mca["url"]), "https://www.kiet.edu/programs/ksoca/MCA")


class PlacementRetrievalTests(unittest.TestCase):
    @patch("app.rag.retriever.query_collection")
    def test_placement_and_mca_metadata_boost_after_existing_distance_filter(self, query_collection):
        query_collection.return_value = [
            {"text": "Placement overview", "metadata": {"category": "placements"}, "distance": 0.30},
            {"text": "MCA placement records", "metadata": {"category": "programs", "programme": "MCA"}, "distance": 0.34},
            {"text": "Admission eligibility", "metadata": {"category": "admissions"}, "distance": 0.31},
            {"text": "Too far", "metadata": {"category": "placements"}, "distance": 0.99},
        ]
        result = retrieve("M.C.A. placement package", top_k=3)
        self.assertEqual(result[0]["text"], "Placement overview")
        self.assertEqual(result[1]["text"], "MCA placement records")
        self.assertNotIn("Too far", [item["text"] for item in result])
        query_collection.assert_called_once_with("MCA placement package", 15)

    @patch("app.rag.pipeline.generate_answer")
    @patch("app.rag.pipeline.retrieve")
    def test_policy_answer_distinguishes_information_from_policy_and_cites_sources(self, retrieve_mock, generate):
        retrieve_mock.return_value = [{
            "text": "MCA placement data",
            "metadata": {
                "source": "https://www.kiet.edu/programs/ksoca/MCA/",
                "source_url": "https://www.kiet.edu/programs/ksoca/MCA/",
                "source_title": "KIET MCA",
                "category": "programs",
                "programme": "MCA",
                "source_type": "webpage",
            },
            "distance": 0.2,
        }]
        generate.return_value = "not used"
        result = answer_question("What is the MCA placement policy?")
        self.assertIn("couldn't verify a specific MCA placement policy", result["answer"])
        self.assertEqual(result["response_type"], "answer")
        self.assertEqual(result["sources"][0]["url"], "https://www.kiet.edu/programs/ksoca/MCA/")
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
