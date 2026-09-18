from __future__ import annotations

from pathlib import Path
from langchain_chroma import Chroma
from src.llm import get_embeddings

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "chroma_db"


def ensure_knowledge_base() -> None:
    """Create the local vector store when a cloud host starts without build artifacts.

    Render's free instances have an ephemeral filesystem, so this fallback keeps
    the deployed demo functional after a restart. It only runs when the store is
    absent and uses the same documented ingestion pipeline as local setup.
    """
    if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
        return
    try:
        from scripts.ingest import main as ingest_knowledge
        ingest_knowledge()
    except Exception as exc:
        raise RuntimeError(
            "The scientific knowledge base could not be prepared. Verify that "
            "OPENAI_API_KEY is configured in the deployment environment, then retry."
        ) from exc


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Return actual Chroma matches, with provenance preserved for citations."""
    ensure_knowledge_base()
    store = Chroma(persist_directory=str(CHROMA_DIR), embedding_function=get_embeddings())
    results = store.similarity_search_with_relevance_scores(query, k=k)
    if not results:
        return []
    return [
        {"content": doc.page_content, "metadata": doc.metadata, "score": round(float(score), 3)}
        for doc, score in results
    ]


def format_context(docs: list[dict]) -> str:
    return "\n\n".join(
        f"SOURCE {i + 1}\nTitle: {d['metadata'].get('title')}\n"
        f"Organization: {d['metadata'].get('organization')}\nYear: {d['metadata'].get('year')}\n"
        f"URL: {d['metadata'].get('source_url')}\nTopic: {d['metadata'].get('topic')}\n"
        f"Excerpt: {d['content']}"
        for i, d in enumerate(docs)
    )
