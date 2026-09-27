"""
api/routes/logs.py
------------------
GET /logs  — Returns agent log entries for the Logs page.

Sources (in order of preference):
  1. Timeline events from RUN_REGISTRY (real per-node steps)
  2. Static fallback lines so the page is never blank

Future upgrade: tail a real log file or push to a ring buffer
from Python's logging handler so every logger.info() call
across all node files appears here automatically.
"""

import time
from fastapi import APIRouter, Query
from agent.run_events import RUN_REGISTRY

router = APIRouter(prefix="/logs", tags=["logs"])


def _level_from_status(status: str) -> str:
    return {"success": "INFO", "running": "INFO", "warning": "WARN", "error": "ERROR"}.get(status, "INFO")


@router.get("")
async def get_logs(limit: int = Query(default=200, le=1000)):
    """
    Returns log entries shaped as {ts, level, source, msg}.
    Pulls from real run timeline events first, then pads with
    static startup lines so the page always has something to show.
    """
    entries = []

    # ── Real timeline events from all known runs ──────────────
    for run in sorted(RUN_REGISTRY.values(), key=lambda r: r.get("started_at", 0)):
        run_id     = run["run_id"]
        alarm_name = run.get("alarm_name", "unknown")

        entries.append({
            "ts":     time.strftime("%H:%M:%S", time.localtime(run.get("started_at", time.time()))),
            "level":  "INFO",
            "source": "api.main",
            "msg":    f"Agent run started: {run_id[:8]}… alarm={alarm_name}",
        })

        for event in run.get("timeline", []):
            entries.append({
                "ts":     event.get("time", "—"),
                "level":  _level_from_status(event.get("status", "success")),
                "source": f"{event.get('stage', 'agent')}_node",
                "msg":    event.get("message", ""),
            })

        status = run.get("status", "running")
        if status in ("completed", "failed"):
            entries.append({
                "ts":     "—",
                "level":  "INFO" if status == "completed" else "ERROR",
                "source": "agent.graph",
                "msg":    f"Agent run {status}: {run_id[:8]}…",
            })

    # ── Static startup lines (always shown) ──────────────────
    startup = [
        {"ts": "—", "level": "INFO", "source": "api.main",    "msg": "CloudOps Agent API starting (env=development)"},
        {"ts": "—", "level": "INFO", "source": "api.main",    "msg": "CloudOps Agent API ready — awaiting alarms"},
    ]

    # Startup lines first, then run events, newest last
    all_entries = startup + entries
    return all_entries[-limit:]
