import unittest
from unittest.mock import Mock, patch

from app.rag import bootstrap, vector_store
from app.rag.document_loader import Document
from app.rag.web_ingest import ingest


class BootstrapTests(unittest.TestCase):
    @patch("app.rag.bootstrap.get_collection")
    def test_populated_index_is_reused_without_ingestion(self, get_collection):
        get_collection.return_value.count.return_value = 126
        # ingest is imported lazily inside the function; patch its defining module.
        with patch("app.rag.web_ingest.ingest") as actual_ingest:
            self.assertEqual(bootstrap.ensure_knowledge_index(), 126)
        actual_ingest.assert_not_called()

    @patch("app.rag.bootstrap.get_collection")
    def test_empty_index_is_seeded_and_chunk_count_is_returned(self, get_collection):
        collection = Mock()
        collection.count.side_effect = [0, 12]
        get_collection.return_value = collection
        with patch("app.rag.web_ingest.ingest", return_value={"failed": 0}) as ingest_sources:
            self.assertEqual(bootstrap.ensure_knowledge_index(), 12)
        ingest_sources.assert_called_once_with()

    def test_repeated_source_upserts_do_not_duplicate_deterministic_chunk_ids(self):
        class Collection:
            def __init__(self):
                self.records = {}

            def delete(self, where):
                self.records = {
                    key: record for key, record in self.records.items()
                    if record["metadata"].get("source") != where["source"]
                }

            def upsert(self, ids, documents, metadatas):
                self.records.update({
                    item_id: {"text": text, "metadata": metadata}
                    for item_id, text, metadata in zip(ids, documents, metadatas)
                })

        collection = Collection()
        document = Document("Official KIET program information", {"source": "https://www.kiet.edu/programs"})
        with patch("app.rag.vector_store.get_collection", return_value=collection):
            vector_store.replace_sources([document], ["https://www.kiet.edu/programs"])
            vector_store.replace_sources([document], ["https://www.kiet.edu/programs"])
        self.assertEqual(len(collection.records), 1)

    def test_unchanged_official_source_is_not_written_again(self):
        registry_entry = {
            "url": "https://www.kiet.edu/programs",
            "title": "KIET Programs",
            "category": "programs",
            "source_type": "webpage",
            "enabled": True,
        }
        with (
            patch("app.rag.web_ingest.load_registry", return_value=[registry_entry]),
            patch("app.rag.web_ingest.load_web_source", return_value=([], "same-content", 100)),
            patch("app.rag.web_ingest.source_has_content_hash", return_value=True),
            patch("app.rag.web_ingest.replace_sources") as replace_sources,
        ):
            summary = ingest()
        self.assertEqual(summary["unchanged"], 1)
        replace_sources.assert_not_called()


if __name__ == "__main__":
    unittest.main()
