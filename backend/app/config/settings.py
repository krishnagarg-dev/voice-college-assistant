import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must list explicit origins; wildcard CORS is not supported")
    return origins


class Settings:
    """Environment-backed settings for API, RAG and LLM configuration."""

    @property
    def cors_origins(self) -> list[str]:
        return _cors_origins()

    @property
    def backend_dir(self) -> Path:
        return BACKEND_DIR

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()

    @property
    def gemini_model(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    @property
    def rag_chunk_size(self) -> int:
        return max(1, int(os.getenv("RAG_CHUNK_SIZE", "800")))

    @property
    def rag_chunk_overlap(self) -> int:
        return max(0, int(os.getenv("RAG_CHUNK_OVERLAP", "150")))

    @property
    def rag_top_k(self) -> int:
        return max(1, int(os.getenv("RAG_TOP_K", "4")))

    @property
    def rag_max_distance(self) -> float:
        return float(os.getenv("RAG_MAX_DISTANCE", "0.60"))

    @property
    def documents_path(self) -> Path:
        return _configured_path("DOCUMENTS_PATH", "data/documents")

    @property
    def vector_db_path(self) -> Path:
        return _configured_path("VECTOR_DB_PATH", "data/chroma")


def _configured_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else BACKEND_DIR / value


settings = Settings()
