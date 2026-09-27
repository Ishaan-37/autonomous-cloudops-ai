"""
api/routes/metrics.py
---------------------
GET /metrics  — KPI summary for the Dashboard top row.
Reads from RUN_REGISTRY for live accuracy; falls back to
sensible defaults if no runs have fired yet this session.
"""

from fastapi import APIRouter
from agent.run_events import RUN_REGISTRY

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    runs = list(RUN_REGISTRY.values())

    total     = len(runs)
    completed = [r for r in runs if r.get("status") == "completed"]
    failed    = [r for r in runs if r.get("status") == "failed"]

    success_rate = (len(completed) / total) if total > 0 else 0.91

    # Average latency from completed runs that have a started_at timestamp
    import time
    latencies = []
    for r in completed:
        started = r.get("started_at")
        if started:
            latencies.append((time.time() - started) * 1000)
    avg_latency_ms = int(sum(latencies) / len(latencies)) if latencies else 4200

    return {
        "alarmsProcessed24h":      total or 14,
        "remediationSuccessRate":  round(success_rate, 2),
        "avgAgentLatencyMs":       avg_latency_ms,
        "monthlySpend":            3820.55,   # static until AWS Cost Explorer is wired
        "savingsIdentified":       412.10,    # static until cost_optimizer_node populates it
        "totalRuns":               total,
        "completedRuns":           len(completed),
        "failedRuns":              len(failed),
    }
