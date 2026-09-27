"""
api/routes/monitoring.py
------------------------
GET /monitoring  — 7-day trend data for the Monitoring page charts.
Currently returns realistic mock trends; swap the arrays for real
Prometheus/CloudWatch queries once those integrations are live.
"""

from fastapi import APIRouter
from agent.run_events import RUN_REGISTRY
import time

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@router.get("")
async def get_monitoring():
    runs = list(RUN_REGISTRY.values())

    # Build per-day alarm counts from real run data if available
    from datetime import datetime, timezone
    day_counts = {d: 0 for d in DAYS}
    for r in runs:
        started = r.get("started_at")
        if started:
            day_name = datetime.fromtimestamp(started, tz=timezone.utc).strftime("%a")
            if day_name in day_counts:
                day_counts[day_name] += 1

    # Merge real counts into mock trend (keeps chart non-empty on first boot)
    mock_alarms   = [9,  12, 8,  15, 11, 5,  14]
    mock_latency  = [3800, 4100, 3950, 5200, 4600, 3400, 4200]
    mock_success  = [0.88, 0.92, 0.85, 0.94, 0.90, 0.96, 0.91]
    mock_tokens   = [42000, 58000, 39000, 71000, 63000, 21000, 55000]

    latency_trend = [
        {
            "day":       DAYS[i],
            "latencyMs": mock_latency[i],
            "alarms":    day_counts.get(DAYS[i], 0) or mock_alarms[i],
        }
        for i in range(7)
    ]

    success_trend = [{"day": DAYS[i], "success": mock_success[i]} for i in range(7)]
    token_usage   = [{"day": DAYS[i], "tokens":  mock_tokens[i]}  for i in range(7)]

    return {
        "latencyTrend":  latency_trend,
        "successTrend":  success_trend,
        "tokenUsage":    token_usage,
    }
