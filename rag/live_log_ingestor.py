"""
rag/live_log_ingestor.py
------------------------
Pulls recent logs from CloudWatch and indexes them into Pinecone
so the agent can retrieve semantically similar past incidents.

Run manually for a one-time backfill:
  python -m rag.live_log_ingestor

Or schedule it (e.g. every 60s via cron/Kubernetes CronJob) to keep
the log index fresh so ingest_node always has recent context.

Requires:
  - AWS credentials with logs:DescribeLogStreams + logs:GetLogEvents
  - PINECONE_API_KEY and LIVE_LOG_INDEX set in .env
  - OPENAI_API_KEY set (for real embeddings)
"""

import os
import time
import uuid
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3
from pinecone import Pinecone

from rag.embedder import create_embedding

load_dotenv()
logger = logging.getLogger(__name__)

LOG_GROUP   = os.getenv("CLOUDWATCH_LOG_GROUP", "/aws/eks/cloudops-staging-cluster/cluster")
BATCH_SIZE  = 50    # upsert this many vectors per Pinecone call
MAX_STREAMS = 5     # how many log streams to read per run
MAX_EVENTS  = 50    # how many events to read per stream

# ── Lazy clients ─────────────────────────────────────────────────
_logs_client = None
_index       = None

def _get_logs_client():
    global _logs_client
    if _logs_client is None:
        _logs_client = boto3.client("logs", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _logs_client

def _get_index():
    global _index
    if _index is None:
        pc     = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _index = pc.Index(os.getenv("LIVE_LOG_INDEX", "cloudops-logs"))
    return _index


# ── Core ingestion ───────────────────────────────────────────────

def ingest_logs() -> int:
    """
    Fetch recent CloudWatch log events and upsert them into Pinecone.
    Returns total number of vectors upserted.
    """
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not set — skipping log ingestion")
        return 0

    logs_client = _get_logs_client()
    index       = _get_index()

    logger.info(f"Starting CloudWatch ingestion from: {LOG_GROUP}")

    try:
        streams = logs_client.describe_log_streams(
            logGroupName=LOG_GROUP,
            orderBy="LastEventTime",
            descending=True,
            limit=MAX_STREAMS,
        )
    except Exception as e:
        logger.error(f"Could not list log streams: {e}")
        return 0

    total   = 0
    vectors = []

    for stream in streams.get("logStreams", []):
        stream_name = stream["logStreamName"]
        logger.info(f"Reading stream: {stream_name}")

        try:
            events = logs_client.get_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=stream_name,
                limit=MAX_EVENTS,
                startFromHead=False,
            )
        except Exception as e:
            logger.warning(f"Could not read stream {stream_name}: {e}")
            continue

        for event in events.get("events", []):
            message = event.get("message", "").strip()
            if not message:
                continue

            ts = datetime.fromtimestamp(
                event["timestamp"] / 1000, tz=timezone.utc
            ).isoformat()

            embedding = create_embedding(message)

            vectors.append({
                "id":     str(uuid.uuid4()),
                "values": embedding,
                "metadata": {
                    "text":        message[:1000],
                    "source":      "cloudwatch",
                    "log_group":   LOG_GROUP,
                    "log_stream":  stream_name,
                    "timestamp":   ts,
                }
            })

            # Upsert in batches to avoid Pinecone request size limits
            if len(vectors) >= BATCH_SIZE:
                index.upsert(vectors=vectors)
                total  += len(vectors)
                vectors = []
                logger.info(f"Upserted batch — total so far: {total}")

    # Flush remaining vectors
    if vectors:
        index.upsert(vectors=vectors)
        total += len(vectors)

    logger.info(f"Log ingestion complete — {total} vectors upserted")
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    count = ingest_logs()
    print(f"\n✅ Done — {count} log vectors upserted to Pinecone")
