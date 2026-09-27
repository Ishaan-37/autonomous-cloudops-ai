"""
agent/run_events.py
--------------------
Shared in-memory run registry + event logging.

WHY THIS EXISTS AS ITS OWN FILE:
  RUN_REGISTRY used to live inside api/main.py. That's fine for the API
  itself, but it means agent/nodes/*.py can't import it without risking
  a circular import (api.main -> agent.graph -> agent.nodes.* -> api.main).
  Putting it here breaks that cycle: both api/main.py and every node file
  can import from agent.run_events safely.

WHAT IT'S FOR:
  Turns the workflow timeline from a single frozen "stage" string into a
  real ordered list of what actually happened, e.g.:

    {
      "run_id": "...",
      "status": "completed",
      "stage": "report",
      "timeline": [
        {"stage": "ingest",  "status": "success", "time": "22:48:01", "message": "Collected alarm metadata"},
        {"stage": "analyze", "status": "warning", "time": "22:48:03", "message": "Pinecone query slow, continuing"},
        {"stage": "plan",    "status": "success", "time": "22:48:05", "message": "Generated remediation plan"},
        {"stage": "report",  "status": "success", "time": "22:48:08", "message": "Report generated"}
      ]
    }

USAGE FROM A NODE FILE (e.g. agent/nodes/ingest_node.py):

    from agent.run_events import log_step

    async def ingest_node(state):
        run_id = state["run_id"]  # adjust to however run_id is actually stored in your state
        log_step(run_id, "ingest", "running", "Collecting alarm context...")
        ...
        log_step(run_id, "ingest", "success", "Collected CloudWatch context")
        return state

STATUS VALUES: "running" | "success" | "warning" | "error"
  These map directly to the colored icons on the frontend timeline.
"""

import time

# run_id -> run info dict
RUN_REGISTRY: dict[str, dict] = {}


def start_run(run_id: str, alarm_name: str, instance: str = "", severity: str = "medium") -> None:
    """Call this the moment a run is created (in _dispatch_alarm / test_trigger)."""
    RUN_REGISTRY[run_id] = {
        "run_id": run_id,
        "alarm_name": alarm_name,
        "instance": instance,
        "severity": severity,
        "status": "running",
        "stage": "ingest",
        "started_at": time.time(),
        "timeline": [],
    }


def log_step(run_id: str, stage: str, status: str, message: str = "") -> None:
    """
    Call this from inside a node as it starts and finishes a step.
    Safe to call even if run_id isn't registered (e.g. during local
    testing of a node in isolation) - it just no-ops instead of crashing.
    """
    if run_id not in RUN_REGISTRY:
        return
    RUN_REGISTRY[run_id]["stage"] = stage
    RUN_REGISTRY[run_id]["timeline"].append({
        "stage": stage,
        "status": status,
        "time": time.strftime("%H:%M:%S"),
        "message": message,
    })


def set_root_cause(run_id: str, root_cause: str) -> None:
    """Call this from analyze_node once the AI has determined a root cause."""
    if run_id in RUN_REGISTRY:
        RUN_REGISTRY[run_id]["root_cause"] = root_cause


def set_plan(run_id: str, plan: str) -> None:
    """Call this from plan_node once a remediation plan is generated."""
    if run_id in RUN_REGISTRY:
        RUN_REGISTRY[run_id]["plan"] = plan


def complete_run(run_id: str, error: str | None = None) -> None:
    """Call this when a run finishes - success or failure."""
    if run_id not in RUN_REGISTRY:
        return
    if error:
        RUN_REGISTRY[run_id]["status"] = "failed"
        RUN_REGISTRY[run_id]["error"] = error
    else:
        RUN_REGISTRY[run_id]["status"] = "completed"
        RUN_REGISTRY[run_id]["stage"] = "report"
