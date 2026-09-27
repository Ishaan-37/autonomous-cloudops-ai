"""
rag/diagnosis_engine.py
-----------------------
RAG-powered diagnosis engine.

Retrieves relevant context from Pinecone and uses it to support
the analyze_node's LLM reasoning. Can also be run standalone for
manual testing from the terminal.

Run from project root:
  python -m rag.diagnosis_engine
"""

import os
import logging
from dotenv import load_dotenv
from pinecone import Pinecone

from rag.embedder import create_embedding

load_dotenv()
logger = logging.getLogger(__name__)

# ── Lazy Pinecone connection ─────────────────────────────────────
_index = None

def _get_index():
    global _index
    if _index is None:
        pc     = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _index = pc.Index(os.getenv("AWS_DOCS_INDEX", "aws-docs"))
    return _index


# ── Core retrieval ───────────────────────────────────────────────

def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Embed the query and fetch the most relevant AWS doc chunks from Pinecone.
    Returns a single formatted string ready to inject into an LLM prompt.
    Returns empty string if Pinecone is unavailable.
    """
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not set — skipping context retrieval")
        return ""

    try:
        embedding = create_embedding(query)
        results   = _get_index().query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
        )
        chunks = []
        for match in results.matches:
            if match.score < 0.4:          # skip low-quality matches
                continue
            text    = match.metadata.get("text", "").strip()
            section = match.metadata.get("section", "AWS Docs")
            source  = match.metadata.get("source", "")
            if text:
                chunks.append(f"[{section}] (score: {match.score:.2f})\n{text}\nSource: {source}")

        return "\n\n---\n\n".join(chunks) if chunks else ""

    except Exception as e:
        logger.error(f"retrieve_context failed: {e}")
        return ""


def analyze_issue(query: str, context: str) -> None:
    """
    Standalone terminal diagnosis — prints retrieved context.
    In the real pipeline, analyze_node passes this context to the LLM
    rather than doing rule-based if/else analysis here.
    """
    print("\n========== RETRIEVED CONTEXT ==========\n")
    if context:
        print(context)
    else:
        print("No relevant context found in Pinecone.")
        print("Check that:")
        print("  1. PINECONE_API_KEY is set in .env")
        print("  2. OPENAI_API_KEY is set (needed for embeddings)")
        print("  3. rag/ingest_aws_docs.py has been run at least once")

    print("\n========== QUERY ==========\n")
    print(query)
    print("\nIn the full pipeline, this context is passed to GPT-4 in analyze_node.py")
    print("for AI-powered root cause analysis instead of hardcoded if/else logic.")


if __name__ == "__main__":
    query   = input("Describe cloud issue: ")
    context = retrieve_context(query)
    analyze_issue(query, context)
