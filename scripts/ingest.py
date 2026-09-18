"""Ingest the small, inspectable starter library into ChromaDB."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.llm import get_embeddings

DOCS = ROOT / "knowledge" / "documents"
DB = ROOT / "chroma_db"


def load_markdown(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"{path.name} needs YAML metadata between --- markers")
    _, front, content = raw.split("---", 2)
    metadata = yaml.safe_load(front)
    required = {"title", "organization", "year", "source_url", "topic"}
    missing = required - metadata.keys()
    if missing: raise ValueError(f"{path.name} missing metadata: {missing}")
    metadata["document"] = path.name
    return Document(page_content=content.strip(), metadata=metadata)


def main() -> None:
    files = sorted(DOCS.glob("*.md"))
    if not files: raise RuntimeError(f"No documents found in {DOCS}")
    documents = [load_markdown(path) for path in files]
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120).split_documents(documents)
    if DB.exists(): shutil.rmtree(DB)
    Chroma.from_documents(chunks, get_embeddings(), persist_directory=str(DB))
    print(f"Ingested {len(files)} documents as {len(chunks)} chunks into {DB}")


if __name__ == "__main__": main()
