"""Shared Chroma embedding provider.

Chroma's default embedding function uses a local all-MiniLM-L6-v2 model. It
needs no API key and the same provider is used for indexing and queries.
"""

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.config.settings import settings


def get_embedding_function() -> DefaultEmbeddingFunction:
    # Keep the model cache within the application's configured local data path.
    # This also avoids writing to a user's global cache directory.
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = str(settings.vector_db_path / "embedding-model")
    return DefaultEmbeddingFunction()
