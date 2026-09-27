"""
rag/ingest_aws_docs.py
----------------------
One-time script: scrapes AWS docs and indexes them into Pinecone.

Run this from the project root:
  python -m rag.ingest_aws_docs

Only needs to be run again if you:
  - Add new URLs to AWS_DOC_URLS
  - Delete/recreate the Pinecone index
  - Change the embedding model

After the embedder.py fix, run this once to replace the old
random-vector embeddings with real semantic ones.
"""

import os
import uuid
import requests
from bs4 import BeautifulSoup
from pinecone import Pinecone
from dotenv import load_dotenv

from rag.embedder import create_embedding   # fixed: use package import

load_dotenv()

# ── Pinecone setup ───────────────────────────────────────────────
pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("AWS_DOCS_INDEX", "aws-docs"))

# ── AWS doc pages to index ───────────────────────────────────────
AWS_DOC_URLS = [
    "https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html",
    "https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html",
    "https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html",
    "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html",
    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring_ec2.html",
]

CHUNK_SIZE  = 500   # characters per chunk
MAX_CHUNKS  = 30    # max chunks per page (keeps costs low during dev)
BATCH_SIZE  = 50    # upsert in batches to avoid Pinecone request limits


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text on word boundaries so chunks don't cut mid-word."""
    words  = text.split()
    chunks = []
    current = []
    length  = 0
    for word in words:
        if length + len(word) + 1 > size and current:
            chunks.append(" ".join(current))
            current = []
            length  = 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def ingest_url(url: str) -> int:
    """Scrape one URL, embed its chunks, upsert to Pinecone. Returns chunk count."""
    print(f"\n→ Ingesting: {url}")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        return 0

    soup   = BeautifulSoup(resp.text, "html.parser")
    # Remove nav/footer noise before extracting text
    for tag in soup(["nav", "footer", "script", "style"]):
        tag.decompose()
    text   = soup.get_text(separator=" ", strip=True)
    chunks = chunk_text(text)[:MAX_CHUNKS]

    vectors = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        embedding = create_embedding(chunk)
        vectors.append({
            "id":     str(uuid.uuid4()),
            "values": embedding,
            "metadata": {
                "text":    chunk,
                "source":  url,
                "section": soup.title.string if soup.title else url,
                "chunk":   i,
            }
        })

    # Upsert in batches
    for i in range(0, len(vectors), BATCH_SIZE):
        index.upsert(vectors=vectors[i:i + BATCH_SIZE])

    print(f"  ✓ Indexed {len(vectors)} chunks")
    return len(vectors)


if __name__ == "__main__":
    total = 0
    for url in AWS_DOC_URLS:
        total += ingest_url(url)
    print(f"\n✅ AWS docs ingestion complete — {total} vectors upserted to '{index.name}'")
