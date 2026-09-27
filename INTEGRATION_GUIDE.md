# Integration Guide — How to Add These 2 Files to Your Project

## Files Generated

```
api/routes/chat.py       ← NEW — AI Chat + SSE streaming
agent/run_events.py      ← UPDATED — added SSE publish hook
```

---

## Step 1 — Replace `agent/run_events.py`

Just replace the existing file with the new one.
The new version has everything the old one had, PLUS the `_publish()` hook
that fires SSE events to connected clients when `log_step()` is called.

---

## Step 2 — Add `api/routes/chat.py`

This is a brand new file. Put it at `api/routes/chat.py`.

---

## Step 3 — Register the router in `api/main.py`

Add these 2 lines to `main.py`:

```python
# EXISTING imports (already there):
from api.routes import metrics as metrics_router
from api.routes import monitoring as monitoring_router
from api.routes import logs as logs_router
from api.routes import kubernetes as kubernetes_router
from api.routes import costs as costs_router

# ADD THIS:
from api.routes import chat as chat_router

# EXISTING includes (already there):
app.include_router(metrics_router.router)
app.include_router(monitoring_router.router)
app.include_router(logs_router.router)
app.include_router(kubernetes_router.router)
app.include_router(costs_router.router)

# ADD THIS:
app.include_router(chat_router.router)
```

---

## Step 4 — Add log_step() calls to your nodes (optional but powerful)

To make the SSE stream show real node progress, add these lines to each node:

### ingest_node.py (already has log_step — verify it's there)
```python
from agent.run_events import log_step

async def ingest_node(state):
    log_step(state["run_id"], "ingest", "running", "Querying Pinecone...")
    # ... your code ...
    log_step(state["run_id"], "ingest", "success", f"Context ready ({len(ctx)} chars)")
```

### analyze_node.py — add these 2 lines
```python
from agent.run_events import log_step

async def analyze_node(state):
    log_step(state["run_id"], "analyze", "running", "GPT-4 analyzing root cause...")
    # ... existing code ...
    log_step(state["run_id"], "analyze", "success",
        f"RCA: {validated.severity}, {validated.confidence:.0%} confidence",
        data={"severity": validated.severity, "confidence": validated.confidence,
              "category": validated.category}
    )
```

### plan_node.py — add these 2 lines
```python
from agent.run_events import log_step

async def plan_node(state):
    log_step(state["run_id"], "plan", "running", "GPT-4 generating remediation plan...")
    # ... existing code ...
    log_step(state["run_id"], "plan", "success",
        f"Plan ready: {validated.action_type} — {len(validated.ssm_commands)} commands",
        data={"action_type": validated.action_type, "requires_approval": validated.requires_approval}
    )
```

### remediate_node.py — add these 2 lines
```python
from agent.run_events import log_step

async def remediate_node(state):
    log_step(state["run_id"], "remediate", "running", "Executing SSM commands on instance...")
    # ... existing code ...
    log_step(state["run_id"], "remediate", "success",
        f"Remediation complete — {len(actions_taken)} actions executed"
    )
```

---

## Step 5 — Test in Swagger

Open `http://localhost:8080/docs`

You will now see a new section: **AI Chat**

```
POST /chat                    ← Ask AI a question (RAG + GPT-4 stream)
GET  /chat/stream/{run_id}    ← Watch an agent run in real time (SSE)
GET  /chat/history            ← Recent chat sessions
POST /chat/explain/{run_id}   ← AI explanation of a past run
```

### Test the streaming chat:
1. Go to `POST /chat`
2. Set `mode: "stream"` and ask: `"Why is my EC2 CPU at 95%?"`
3. Click Execute
4. Watch the response appear word by word in the response body

### Test the SSE run stream:
1. Fire `POST /trigger/test` → copy the `run_id`
2. Open `GET /chat/stream/{run_id}` with that run_id
3. Click Execute
4. Watch events fire as the agent runs each node

---

## What the Swagger response looks like

### POST /chat (mode=stream) response:
```
data: {"type": "status", "message": "🔍 Searching Pinecone for similar incidents...", "run_id": "abc-123"}

data: {"type": "rag_context", "logs_found": 3, "docs_found": 2, "context_chars": 1842, "top_log_score": 0.847}

data: {"type": "status", "message": "🧠 GPT-4 analyzing with RAG context..."}

data: {"type": "token", "content": "Based"}
data: {"type": "token", "content": " on"}
data: {"type": "token", "content": " the"}
data: {"type": "token", "content": " retrieved"}
data: {"type": "token", "content": " logs"}
...

data: {"type": "done", "run_id": "abc-123", "total_tokens": 312, "latency_ms": 2341, "logs_used": 3, "docs_used": 2}
```

### GET /chat/stream/{run_id} response:
```
data: {"type": "connected", "run_id": "abc-123", "message": "Listening for agent events..."}

data: {"type": "node_started",  "stage": "ingest",   "message": "Querying Pinecone..."}
data: {"type": "node_complete", "stage": "ingest",   "message": "Context ready (2341 chars)"}

data: {"type": "node_started",  "stage": "analyze",  "message": "GPT-4 analyzing root cause..."}
data: {"type": "node_complete", "stage": "analyze",  "message": "RCA: HIGH, 91% confidence",
       "severity": "HIGH", "confidence": 0.91, "category": "memory"}

data: {"type": "node_started",  "stage": "plan",     "message": "Generating remediation plan..."}
data: {"type": "node_complete", "stage": "plan",     "message": "Plan: auto_safe, 2 commands"}

data: {"type": "node_started",  "stage": "remediate","message": "Executing SSM commands..."}
data: {"type": "node_complete", "stage": "remediate","message": "2 actions executed"}

data: {"type": "run_complete",  "status": "completed", "duration_ms": 47823}
```

---

## Interview Talking Points (for these new files)

### "What is SSE and why did you use it over WebSockets?"
> "SSE is Server-Sent Events — the server pushes events to the client over a
> single HTTP connection. It's one-directional: server → client. I used it
> because the agent runs asynchronously in the background and I need to push
> progress updates to the UI/Swagger without the client polling. WebSocket
> would be overkill — I don't need the client to send data mid-stream.
> SSE auto-reconnects, works over HTTP/1.1, and is simpler to implement."

### "How does the streaming chat work?"
> "OpenAI's API supports stream=True, which returns an async generator.
> Each iteration yields a chunk with a delta — one or a few tokens.
> I iterate over that generator and yield each token as an SSE event
> formatted as 'data: {json}\n\n'. The client's EventSource reads these
> and appends each token to the UI — creating the typing animation effect."

### "How do nodes publish SSE events without circular imports?"
> "run_events.py is imported by nodes. chat.py (which has the SSE subscriber
> registry) imports from run_events.py. If run_events.py imported from chat.py,
> that would be circular. I broke the cycle with a lazy import inside the
> _publish() function — it only imports chat.publish_run_event at call time,
> not at module load time. By then, all modules are fully loaded."

### "What happens if no one is watching the SSE stream?"
> "_SSE_SUBSCRIBERS[run_id] is an empty list. The for loop in _publish() has
> nothing to iterate — it's a no-op. Zero overhead when no clients connected."

### "How do you handle a client disconnecting mid-stream?"
> "The SSE generator checks 'await request.is_disconnected()' on every loop
> iteration. If true, it breaks out of the loop and the finally block removes
> the client's queue from _SSE_SUBSCRIBERS. No memory leak."
