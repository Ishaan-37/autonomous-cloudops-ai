"""
rag/embedder.py
---------------
Handles all embedding creation and Pinecone vector search.

WHAT THIS FILE DOES:
  1. create_embedding(text) — converts text into a 1536-dim vector using
     OpenAI's text-embedding-3-small model. Used when indexing new logs
     and when querying for similar content.

  2. query_logs(query_text, top_k) — finds past log events semantically
     similar to the query. Queries the cloudops-logs Pinecone index.

  3. query_docs(query_text, top_k) — finds relevant AWS documentation.
     Queries the aws-docs Pinecone index.

  4. format_rag_context(logs, docs) — formats search results into a
     single LLM-ready context string.

DEV MODE:
  If PINECONE_API_KEY or OPENAI_API_KEY are missing, all functions fall
  back gracefully (empty results) instead of crashing. This keeps the
  agent pipeline running even without live credentials.
"""

import logging
import os

logger = logging.getLogger(__name__)

# ── Index names (match what you created in Pinecone dashboard) ──
LOG_INDEX_NAME = os.getenv("PINECONE_LOG_INDEX",  "cloudops-logs")
DOC_INDEX_NAME = os.getenv("PINECONE_DOCS_INDEX", "aws-docs")


# ── Lazy clients (only created when first needed) ────────────────
_openai_client  = None
_pinecone_logs  = None
_pinecone_docs  = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _get_pinecone_index(index_name: str):
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return pc.Index(index_name)


def _get_log_index():
    global _pinecone_logs
    if _pinecone_logs is None:
        _pinecone_logs = _get_pinecone_index(LOG_INDEX_NAME)
    return _pinecone_logs


def _get_doc_index():
    global _pinecone_docs
    if _pinecone_docs is None:
        _pinecone_docs = _get_pinecone_index(DOC_INDEX_NAME)
    return _pinecone_docs


# ── Core embedding function ──────────────────────────────────────

def create_embedding(text: str) -> list[float]:
    """
    Convert text into a 1536-dimensional embedding vector using
    OpenAI text-embedding-3-small.

    Falls back to a zero vector if OpenAI is unavailable, so callers
    don't crash — but Pinecone search results will be meaningless until
    a real key is configured.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — returning zero vector")
        return [0.0] * 1536

    try:
        client = _get_openai()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],  # model limit
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"create_embedding failed: {e}")
        return [0.0] * 1536


# ── Pinecone search functions ────────────────────────────────────

async def query_logs(query_text: str, top_k: int = 5) -> list[dict]:
    """
    Find past log events semantically similar to query_text.
    Returns a list of dicts with keys: text, score, source, timestamp.
    Returns empty list if Pinecone is unavailable.
    """
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not set — skipping log query")
        return []

    try:
        vector = create_embedding(query_text)
        index  = _get_log_index()
        result = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {
                "text":      match.metadata.get("text", ""),
                "score":     match.score,
                "source":    match.metadata.get("source", "cloudwatch"),
                "timestamp": match.metadata.get("timestamp", ""),
            }
            for match in result.matches
            if match.score > 0.5  # filter out low-quality matches
        ]
    except Exception as e:
        logger.error(f"query_logs failed: {e}")
        return []


async def query_docs(query_text: str, top_k: int = 3) -> list[dict]:
    """
    Find relevant AWS documentation sections for query_text.
    Returns a list of dicts with keys: text, score, section, source.
    Returns empty list if Pinecone is unavailable.
    """
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not set — skipping doc query")
        return []

    try:
        vector = create_embedding(query_text)
        index  = _get_doc_index()
        result = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {
                "text":    match.metadata.get("text", ""),
                "score":   match.score,
                "section": match.metadata.get("section", "AWS Docs"),
                "source":  match.metadata.get("source", ""),
            }
            for match in result.matches
            if match.score > 0.5
        ]
    except Exception as e:
        logger.error(f"query_docs failed: {e}")
        return []


# ── Format for LLM prompt ────────────────────────────────────────

def format_rag_context(logs: list[dict], docs: list[dict]) -> str:
    """
    Combine log results and doc results into a single LLM context string.
    """
    parts = []

    if logs:
        parts.append("=== SIMILAR PAST LOG EVENTS ===")
        for i, log in enumerate(logs, 1):
            score = log.get("score", 0)
            ts    = log.get("timestamp", "")
            text  = log.get("text", "")[:500]
            parts.append(f"[{i}] (similarity: {score:.2f}) {ts}\n{text}")
    else:
        parts.append("=== SIMILAR PAST LOG EVENTS ===\nNone found.")

    if docs:
        parts.append("\n=== RELEVANT AWS DOCUMENTATION ===")
        for i, doc in enumerate(docs, 1):
            section = doc.get("section", "AWS Docs")
            text    = doc.get("text", "")[:800]
            parts.append(f"[{i}] {section}\n{text}")
    else:
        parts.append("\n=== RELEVANT AWS DOCUMENTATION ===\nNone found.")

    return "\n\n".join(parts)
