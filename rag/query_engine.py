"""
rag/query_engine.py
-------------------
Search interface for the AWS docs Pinecone index.

Uses the shared create_embedding() from rag/embedder.py so that
indexing and querying always use the same model — no more fake vectors.

Can be run standalone for testing:
  python -m rag.query_engine
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone

from rag.embedder import create_embedding

load_dotenv()

# Lazy index — only connects when first used
_index = None

def _get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _index = pc.Index(os.getenv("AWS_DOCS_INDEX", "aws-docs"))
    return _index


def search_docs(query: str, top_k: int = 3) -> list[dict]:
    """
    Search the AWS docs Pinecone index for content relevant to query.
    Returns a list of dicts with keys: text, score, section, source.
    Returns empty list if Pinecone is unavailable.
    """
    embedding = create_embedding(query)
    results   = _get_index().query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
    )
    return [
        {
            "text":    m.metadata.get("text", ""),
            "score":   m.score,
            "section": m.metadata.get("section", "AWS Docs"),
            "source":  m.metadata.get("source", ""),
        }
        for m in results.matches
    ]


if __name__ == "__main__":
    query = input("Ask AWS issue: ")
    hits  = search_docs(query)
    if not hits:
        print("No results found.")
    else:
        print(f"\nTop {len(hits)} matches:\n")
        for i, h in enumerate(hits, 1):
            print(f"[{i}] {h['section']} (score: {h['score']:.2f})")
            print(h["text"][:500])
            print("\n" + "-" * 40 + "\n")
