"""
api/routes/chat.py
------------------
ADVANCED AI CHAT ENDPOINT WITH REAL-TIME SSE STREAMING

This file adds two things your project was missing:

  1. POST /chat
       - User sends a natural language question about their infra
       - RAG fetches relevant logs + AWS docs from Pinecone
       - GPT-4 streams the answer token-by-token back to the client
       - Swagger shows typing animation as AI responds

  2. GET /chat/stream/{run_id}
       - Server-Sent Events (SSE) stream for any active agent run
       - Frontend / Swagger can watch a run's progress in real time
       - Each node completion fires an event: ingest → analyze → plan → ...

WHY SSE INSTEAD OF WEBSOCKET?
  SSE = server pushes to client (one-way). Perfect for:
    - Streaming LLM tokens (server sends, client reads)
    - Progress events (server fires, client listens)
  WebSocket = bi-directional. Needed only if client also sends data mid-stream.
  SSE is simpler, HTTP/1.1 compatible, auto-reconnects, and enough for this.

HOW STREAMING WORKS (token by token):
  OpenAI stream=True → returns an async generator
  For each chunk → extract delta.content → yield to SSE
  Client sees words appear one-by-one (like ChatGPT)

RAG PIPELINE INSIDE CHAT:
  User query → create_embedding() → Pinecone query (logs + docs)
  → format_rag_context() → GPT-4 system prompt + context
  → stream response → SSE to client

ADD TO main.py:
  from api.routes import chat as chat_router
  app.include_router(chat_router.router)
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel, Field

from agent.run_events import RUN_REGISTRY
from rag.embedder import query_logs, query_docs, format_rag_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["AI Chat"])

oai = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# ── In-memory SSE subscriber registry ─────────────────────────
# run_id → list of asyncio.Queue objects (one per connected SSE client)
# When a node fires log_step(), it puts an event into each queue.
# The SSE generator reads from the queue and sends to the client.
_SSE_SUBSCRIBERS: dict[str, list[asyncio.Queue]] = {}


# ═══════════════════════════════════════════════════════════════
# SCHEMA
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """
    What the user sends to /chat.

    Example:
      {
        "question": "Why is my EC2 CPU suddenly at 95%?",
        "context":  "Instance i-0abc123, us-east-1, t3.medium",
        "mode":     "stream"
      }
    """
    question: str  = Field(...,  min_length=5, max_length=2000,
                           description="Natural language question about your infrastructure")
    context:  str  = Field("",   max_length=500,
                           description="Optional extra context: instance ID, service name, region")
    mode:     str  = Field("stream",
                           description="'stream' for token streaming, 'full' for complete response")
    top_k_logs: int = Field(5,   ge=1, le=10,
                             description="How many similar past log events to retrieve from Pinecone")
    top_k_docs: int = Field(3,   ge=1, le=10,
                             description="How many AWS doc sections to retrieve from Pinecone")


class ChatResponse(BaseModel):
    """Returned by /chat when mode='full'."""
    answer:          str
    sources_used:    dict        # { "pinecone_logs": int, "pinecone_docs": int }
    rag_context_len: int         # characters of context injected into prompt
    latency_ms:      int
    model:           str
    run_id:          str


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """
You are CloudOps AI — an expert Site Reliability Engineer assistant embedded in an
autonomous AWS infrastructure monitoring platform.

YOUR KNOWLEDGE SOURCES (in priority order):
  1. RETRIEVED LOG EVENTS  — real past incidents from this infrastructure (highest trust)
  2. RETRIEVED AWS DOCS    — official AWS documentation (high trust)
  3. YOUR TRAINING DATA    — general SRE / cloud knowledge (use when above are silent)

RULES:
  - Be direct and specific. Skip filler phrases like "Great question!" or "Certainly!"
  - If retrieved logs show a past incident, reference it explicitly with its timestamp
  - If you see a clear root cause in the logs, state it confidently
  - If uncertain, say so and suggest what to investigate next
  - Never invent instance IDs, IP addresses, or metric values not in the provided context
  - Format code, commands, and config values in markdown code blocks
  - Keep answers focused — SREs are busy. No padding.

WHEN LOGS ARE PRESENT:
  Lead with what the logs actually show, then explain the cause, then suggest the fix.

WHEN NO LOGS ARE RETRIEVED:
  Give general SRE guidance and clearly note you don't have specific log data.
""".strip()


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 1: POST /chat  — AI Q&A with RAG + Streaming
# ═══════════════════════════════════════════════════════════════

@router.post(
    "",
    summary="Ask CloudOps AI a question (RAG + GPT-4 streaming)",
    description="""
## What this does

1. Takes your natural language question about AWS infrastructure
2. Embeds the question using `text-embedding-3-small` (1536 dimensions)
3. Queries **Pinecone `cloudops-logs`** index → retrieves top similar past log events
4. Queries **Pinecone `aws-docs`** index → retrieves relevant AWS documentation
5. Injects retrieved context into GPT-4's prompt (RAG)
6. Streams GPT-4's answer **token by token** back to you

## Modes

| mode | behavior |
|------|----------|
| `stream` | Response streams token-by-token (SSE format). Watch it type in real time. |
| `full`   | Waits for complete response, returns JSON with metadata. |

## Example questions
- "Why is my EC2 CPU suddenly at 95%?"
- "What causes OOM kills in EKS pods?"
- "How do I diagnose high memory usage on i-0abc123?"
- "Why did the payment-service restart 3 times last night?"
""",
    response_description="Streaming SSE text (mode=stream) or JSON ChatResponse (mode=full)",
)
async def chat(req: ChatRequest):
    """
    RAG-powered AI chat endpoint.

    - mode='stream': returns StreamingResponse (SSE) — watch tokens appear
    - mode='full':   returns complete JSON response with metadata
    """
    chat_run_id = str(uuid.uuid4())

    if req.mode == "stream":
        return StreamingResponse(
            _stream_chat_response(req, chat_run_id),
            media_type="text/event-stream",
            headers={
                "X-Run-ID":          chat_run_id,
                "Cache-Control":     "no-cache",
                "X-Accel-Buffering": "no",   # disable nginx buffering
            },
        )
    else:
        return await _full_chat_response(req, chat_run_id)


async def _stream_chat_response(req: ChatRequest, run_id: str) -> AsyncGenerator[str, None]:
    """
    Core streaming generator.

    Yields SSE-formatted events:
      data: {"type": "rag_context", "logs_found": 3, "docs_found": 2}
      data: {"type": "token", "content": "The"}
      data: {"type": "token", "content": " root"}
      data: {"type": "done", "total_tokens": 142, "latency_ms": 1823}
      data: {"type": "error", "message": "..."}

    SSE format: each line starts with "data: ", ends with double newline.
    """
    t_start = time.time()

    # ── Step 1: RAG — Pinecone retrieval ──────────────────────
    yield _sse_event("status", {"message": "🔍 Searching Pinecone for similar incidents...", "run_id": run_id})

    try:
        log_results, doc_results = await _fetch_rag_context(req)
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        log_results, doc_results = [], []
        yield _sse_event("warning", {"message": "⚠️ Pinecone unavailable — answering from GPT-4 only"})

    rag_context = format_rag_context(log_results, doc_results)

    # Tell the client what RAG found — useful for debugging
    yield _sse_event("rag_context", {
        "logs_found":   len(log_results),
        "docs_found":   len(doc_results),
        "context_chars": len(rag_context),
        "top_log_score": round(log_results[0]["score"], 3) if log_results else None,
    })

    # ── Step 2: Build GPT-4 prompt ────────────────────────────
    yield _sse_event("status", {"message": "🧠 GPT-4 analyzing with RAG context..."})

    user_message = _build_user_message(req, rag_context)

    # ── Step 3: Stream GPT-4 response token by token ──────────
    total_tokens = 0
    full_response = []

    try:
        stream = await oai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.3,      # Slightly higher than RCA — allows more explanation
            max_tokens=1500,
            stream=True,          # ← THE KEY: async token generator
            timeout=60,
        )

        async for chunk in stream:
            # Each chunk has one token (or empty delta at the end)
            delta = chunk.choices[0].delta
            if delta.content:
                token = delta.content
                full_response.append(token)
                total_tokens += 1
                # Yield each token as an SSE event
                yield _sse_event("token", {"content": token})

    except Exception as e:
        logger.error(f"GPT-4 stream error: {e}")
        yield _sse_event("error", {"message": f"GPT-4 error: {str(e)}"})
        return

    # ── Step 4: Done event with metadata ─────────────────────
    latency_ms = int((time.time() - t_start) * 1000)
    yield _sse_event("done", {
        "run_id":         run_id,
        "total_tokens":   total_tokens,
        "latency_ms":     latency_ms,
        "logs_used":      len(log_results),
        "docs_used":      len(doc_results),
        "model":          "gpt-4o",
        "timestamp":      datetime.now(tz=timezone.utc).isoformat(),
    })

    logger.info(f"[chat/{run_id}] Streamed {total_tokens} tokens in {latency_ms}ms "
                f"(logs={len(log_results)}, docs={len(doc_results)})")


async def _full_chat_response(req: ChatRequest, run_id: str) -> ChatResponse:
    """
    Non-streaming version — waits for the full GPT-4 response, returns JSON.
    Good for programmatic use / Swagger testing.
    """
    t_start = time.time()

    try:
        log_results, doc_results = await _fetch_rag_context(req)
    except Exception:
        log_results, doc_results = [], []

    rag_context  = format_rag_context(log_results, doc_results)
    user_message = _build_user_message(req, rag_context)

    response = await oai.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1500,
        stream=False,   # full response
        timeout=60,
    )

    answer     = response.choices[0].message.content
    latency_ms = int((time.time() - t_start) * 1000)

    return ChatResponse(
        answer=answer,
        sources_used={"pinecone_logs": len(log_results), "pinecone_docs": len(doc_results)},
        rag_context_len=len(rag_context),
        latency_ms=latency_ms,
        model="llama-3.3-70b-versatile",
        run_id=run_id,
    )


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 2: GET /chat/stream/{run_id} — Live Agent Run SSE
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/stream/{run_id}",
    summary="Real-time SSE stream for an active agent run",
    description="""
## What this does

Opens a **Server-Sent Events (SSE)** stream for an active agent run.

As the LangGraph agent progresses through its nodes, this endpoint
fires events that the frontend (or Swagger) can listen to in real time:

```
data: {"type": "node_started",   "node": "ingest_node",   "ts": "..."}
data: {"type": "node_complete",  "node": "analyze_node",  "severity": "HIGH", "confidence": 0.91}
data: {"type": "node_started",   "node": "plan_node",     "ts": "..."}
data: {"type": "approval_needed","message": "Risky action — waiting for human approval"}
data: {"type": "node_complete",  "node": "remediate_node","actions": [...]}
data: {"type": "run_complete",   "status": "success",     "duration_ms": 47823}
```

## How to test in Swagger

1. Fire `POST /trigger/test` → copy the `run_id`
2. Open `GET /chat/stream/{run_id}` with that `run_id`
3. Watch events arrive as the agent runs

## Event types

| type | when it fires |
|------|--------------|
| `connected` | SSE connection established |
| `node_started` | A LangGraph node began executing |
| `node_complete` | A node finished with its output summary |
| `approval_needed` | Agent paused waiting for human approval |
| `run_complete` | Full pipeline finished |
| `heartbeat` | Sent every 15s to keep connection alive |
| `error` | Something failed |
""",
)
async def stream_run(run_id: str, request: Request):
    """
    SSE stream for an active agent run.
    Publishes real-time events as the LangGraph graph moves through nodes.
    """
    run = RUN_REGISTRY.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return StreamingResponse(
        _run_event_stream(run_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


async def _run_event_stream(run_id: str, request: Request) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events for a specific agent run.

    Uses a per-run asyncio.Queue. When agent nodes call publish_run_event(),
    events are put into the queue and immediately streamed to the client.
    """
    # Register this client's queue for the run
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    if run_id not in _SSE_SUBSCRIBERS:
        _SSE_SUBSCRIBERS[run_id] = []
    _SSE_SUBSCRIBERS[run_id].append(queue)

    logger.info(f"SSE client connected for run {run_id[:8]}")
    yield _sse_event("connected", {"run_id": run_id, "message": "Listening for agent events..."})

    # Replay any events that already happened (for late-joining clients)
    run = RUN_REGISTRY.get(run_id, {})
    for past_event in run.get("events", []):
        yield _sse_event("node_complete", past_event)

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Check if run is already done
            current_run = RUN_REGISTRY.get(run_id, {})
            if current_run.get("status") in ("completed", "failed"):
                yield _sse_event("run_complete", {
                    "run_id":    run_id,
                    "status":    current_run["status"],
                    "stages":    current_run.get("stages", {}),
                    "error":     current_run.get("error"),
                })
                break

            # Wait for next event (or heartbeat timeout)
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield _sse_event(event["type"], event["data"])

                # If the event says the run is done, close the stream
                if event["type"] == "run_complete":
                    break

            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive (nginx/proxies close idle SSE)
                yield _sse_event("heartbeat", {"ts": datetime.now(tz=timezone.utc).isoformat()})

    finally:
        # Clean up this client's queue
        if run_id in _SSE_SUBSCRIBERS:
            try:
                _SSE_SUBSCRIBERS[run_id].remove(queue)
            except ValueError:
                pass
            if not _SSE_SUBSCRIBERS[run_id]:
                del _SSE_SUBSCRIBERS[run_id]
        logger.info(f"SSE client disconnected from run {run_id[:8]}")


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 3: GET /chat/history — Recent Chat Sessions
# ═══════════════════════════════════════════════════════════════

_CHAT_HISTORY: list[dict] = []   # In-memory, last 50 sessions


@router.get(
    "/history",
    summary="Recent AI chat sessions",
    description="Returns the last 50 chat sessions — question, answer summary, RAG sources used.",
)
async def chat_history():
    return {
        "sessions": _CHAT_HISTORY[-50:],
        "count":    len(_CHAT_HISTORY),
    }


# ═══════════════════════════════════════════════════════════════
# ENDPOINT 4: POST /chat/explain/{run_id} — Explain a Past Run
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/explain/{run_id}",
    summary="AI explanation of a past agent run",
    description="""
Ask GPT-4 to explain a completed agent run in plain English.

Useful when:
- A stakeholder asks "what happened to prod last night?"
- You want a human-readable summary of the RCA + remediation
- You need to write a postmortem

GPT-4 reads the run's full state (alarm, root cause, plan, actions taken)
and generates a clear narrative explanation.
""",
)
async def explain_run(run_id: str):
    """Generate a plain-English explanation of a completed agent run."""
    run = RUN_REGISTRY.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    run_summary = json.dumps({
        "alarm":      run.get("alarm_name"),
        "status":     run.get("status"),
        "started_at": run.get("started_at"),
        "stages":     run.get("stages", {}),
        "error":      run.get("error"),
        "events":     run.get("events", [])[-10:],  # last 10 events
    }, indent=2)

    prompt = f"""
You are a CloudOps AI assistant. A user wants a clear explanation of an automated
infrastructure incident response run.

Here is the run data:
{run_summary}

Write a clear 3-4 paragraph explanation covering:
1. What alarm fired and what likely caused it
2. What the AI agent did (which stages ran)
3. What the outcome was (fixed, escalated, or failed)
4. What a human should do next (if anything)

Write in plain English, as if explaining to a senior engineer who wasn't on-call.
""".strip()

    response = await oai.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=800,
    )

    explanation = response.choices[0].message.content

    return {
        "run_id":      run_id,
        "explanation": explanation,
        "model":       "gpt-4o",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# PUBLIC HELPER — called by agent nodes to fire SSE events
# ═══════════════════════════════════════════════════════════════

def publish_run_event(run_id: str, event_type: str, data: dict):
    """
    Called by LangGraph nodes to push real-time events to SSE clients.

    Usage in any node file:
      from api.routes.chat import publish_run_event
      publish_run_event(state["run_id"], "node_complete", {
          "node":       "analyze_node",
          "severity":   rca["severity"],
          "confidence": rca["confidence"],
          "root_cause": rca["root_cause"][:200],
      })

    This puts the event into every connected client's SSE queue.
    Thread-safe because asyncio.Queue is used (no locks needed).
    """
    subscribers = _SSE_SUBSCRIBERS.get(run_id, [])
    event = {"type": event_type, "data": data}
    for queue in subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for run {run_id[:8]} — dropping event")


# ═══════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════

async def _fetch_rag_context(req: ChatRequest) -> tuple[list, list]:
    """
    Run both Pinecone queries concurrently using asyncio.gather().
    Returns (log_results, doc_results).

    If Pinecone is down, both return empty lists — graceful degradation.
    """
    query = f"{req.question} {req.context}".strip()

    log_results, doc_results = await asyncio.gather(
        query_logs(query_text=query, top_k=req.top_k_logs),
        query_docs(query_text=query, top_k=req.top_k_docs),
        return_exceptions=True,
    )

    # Handle partial failures
    if isinstance(log_results, Exception):
        logger.warning(f"Pinecone log query failed: {log_results}")
        log_results = []
    if isinstance(doc_results, Exception):
        logger.warning(f"Pinecone doc query failed: {doc_results}")
        doc_results = []

    return log_results, doc_results


def _build_user_message(req: ChatRequest, rag_context: str) -> str:
    """
    Build the final user message for GPT-4.
    Combines the user's question, extra context, and retrieved RAG context.
    """
    parts = []

    if req.context:
        parts.append(f"CONTEXT:\n{req.context}")

    if rag_context and "No similar" not in rag_context:
        parts.append(rag_context)
    else:
        parts.append("NOTE: No similar past incidents found in Pinecone. "
                     "Answering from AWS documentation and general SRE knowledge.")

    parts.append(f"QUESTION:\n{req.question}")

    return "\n\n".join(parts)


def _sse_event(event_type: str, data: dict) -> str:
    """
    Format a Server-Sent Event.

    SSE wire format (RFC):
      data: <json>\n\n

    The double newline signals the end of one event.
    The client's EventSource fires an 'onmessage' for each event.
    """
    payload = json.dumps({"type": event_type, **data}, default=str)
    return f"data: {payload}\n\n"
