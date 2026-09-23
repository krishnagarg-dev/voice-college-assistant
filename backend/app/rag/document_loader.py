from pathlib import Path
from dataclasses import dataclass, field

from pypdf import PdfReader


SUPPORTED_SUFFIXES = {".pdf", ".txt"}


@dataclass
class Document:
    page_content: str
    metadata: dict = field(default_factory=dict)


def find_documents(documents_dir: Path) -> list[Path]:
    """Return supported files under the knowledge-base directory."""
    if not documents_dir.exists():
        return []
    return sorted(
        path for path in documents_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def load_document(path: Path) -> list[Document]:
    """Load a TXT as one document or a PDF as one document per page."""
    suffix = path.suffix.lower()
    source = path.name

    if suffix == ".txt":
        text = path.read_text(encoding="utf-8-sig").strip()
        # This repository fixture explicitly identifies itself as invented data.
        # Keep the file for local pipeline development, but never index it as KIET knowledge.
        if text.startswith("SAMPLE DATA FOR PIPELINE TESTING ONLY"):
            return []
        return [Document(page_content=text, metadata={"source": source, "source_type": "file"})] if text else []

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(Document(
                    page_content=text,
                    metadata={"source": source, "source_type": "file", "page": page_number},
                ))
        return pages

    raise ValueError(f"Unsupported document type: {suffix}")


def load_documents(paths: list[Path]) -> tuple[list[Document], list[dict[str, str]]]:
    """Load multiple files while isolating individual corrupt/invalid files."""
    loaded: list[Document] = []
    errors: list[dict[str, str]] = []
    for path in paths:
        try:
            loaded.extend(load_document(path))
        except Exception as exc:
            errors.append({"source": path.name, "error": str(exc)})
    return loaded, errors
