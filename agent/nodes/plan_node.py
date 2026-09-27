from dotenv import load_dotenv
load_dotenv()
"""
agent/nodes/plan_node.py
------------------------
NODE 3 OF 6.
"""

import json
import logging
import os

from groq import AsyncGroq
from pydantic import BaseModel, Field, validator

from agent.state import AgentState, FixPlan
from agent.run_events import log_step

logger = logging.getLogger(__name__)
oai = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

ALWAYS_SAFE_ACTIONS = {
    "disk_cleanup":      "sudo journalctl --vacuum-size=500M && sudo apt-get clean",
    "restart_service":   "sudo systemctl restart {service_name}",
    "clear_tmp":         "sudo find /tmp -type f -atime +1 -delete",
    "flush_cache":       "sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'",
    "kill_zombie_procs": "sudo pkill -TERM -P 1 defunct || true",
}

RISKY_ACTIONS = {
    "reboot_instance",
    "scale_out_nodegroup",
    "terminate_instance",
    "increase_instance_type",
    "modify_security_group",
    "delete_old_snapshots",
}

PLAN_SYSTEM_PROMPT = """
You are a Senior Site Reliability Engineer creating a remediation plan.
You have already analyzed the root cause. Now create the SAFEST possible fix.

ACTION TYPE RULES (follow these strictly):
- auto_safe:   Only use if the action is FULLY reversible and risk is LOW.
- auto_risky:  Use when automated fix is possible but requires human approval.
- manual_only: Use when the fix is complex or ambiguous.
- no_action:   Use when the alarm is informational or already self-resolved.

OUTPUT FORMAT:
Respond ONLY with valid JSON. No prose. No markdown.

{
  "summary": "One-line description of the fix",
  "steps": ["Step 1: ...", "Step 2: ..."],
  "action_type": "auto_safe",
  "estimated_risk": "low",
  "estimated_time": "30 seconds",
  "rollback_plan": "If the fix fails, do X to revert",
  "requires_approval": false,
  "ssm_commands": ["sudo journalctl --vacuum-size=500M"],
  "notes": "Any important context or warnings"
}
""".strip()


class FixPlanOutput(BaseModel):
    summary:           str
    steps:             list[str]
    action_type:       str
    estimated_risk:    str
    estimated_time:    str
    rollback_plan:     str
    requires_approval: bool
    ssm_commands:      list[str] = []
    notes:             str = ""

    @validator("action_type")
    def validate_action_type(cls, v):
        allowed = {"auto_safe", "auto_risky", "manual_only", "no_action"}
        return v if v in allowed else "manual_only"

    @validator("estimated_risk")
    def validate_risk(cls, v):
        allowed = {"low", "medium", "high"}
        return v.lower() if v.lower() in allowed else "high"


async def plan_node(state: AgentState) -> dict:
    logger.info(f"[{state['run_id']}] plan_node started")
    log_step(state["run_id"], "plan", "running", "Generating remediation plan...")

    rca   = state.get("root_cause", {})
    alert = state["alert"]

    if not rca:
        log_step(state["run_id"], "plan", "failed", "No root cause available")
        return {
            "fix_plan":     _manual_only_plan("No root cause analysis available"),
            "node_history": ["plan_node"],
            "errors":       ["plan_node: no root_cause in state"],
        }

    user_message = f"""
ROOT CAUSE ANALYSIS:
{json.dumps(rca, indent=2)}

ORIGINAL ALARM:
Name:   {alert.get('AlarmName')}
Reason: {alert.get('StateReason')}

AVAILABLE SAFE ACTIONS (auto_safe only):
{json.dumps(list(ALWAYS_SAFE_ACTIONS.keys()), indent=2)}

Create the remediation plan. Output valid JSON only.
""".strip()

    try:
        response = await oai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            
            temperature=0.1,
            max_tokens=4000,
        )

        raw_json  = response.choices[0].message.content
        raw_json = raw_json.strip()
         # Remove <think>...</think> tags
        if "<think>" in raw_json:
            if "</think>" in raw_json:
                raw_json = raw_json.split("</think>")[-1].strip()
         # Clean markdown fences
        if "```" in raw_json:
            parts = raw_json.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw_json = part
                    break
        plan_data = json.loads(raw_json)
        validated = FixPlanOutput(**plan_data)

        if validated.action_type == "auto_safe":
            if _commands_look_risky(validated.ssm_commands):
                validated.action_type     = "auto_risky"
                validated.requires_approval = True

        if rca.get("severity") == "CRITICAL":
            validated.requires_approval = True
            if validated.action_type == "auto_safe":
                validated.action_type = "auto_risky"

        fix_plan: FixPlan = {
            "summary":           validated.summary,
            "steps":             validated.steps,
            "action_type":       validated.action_type,
            "estimated_risk":    validated.estimated_risk,
            "estimated_time":    validated.estimated_time,
            "rollback_plan":     validated.rollback_plan,
            "requires_approval": validated.requires_approval,
        }
        # Force auto_risky for demo
        fix_plan["action_type"]       = "auto_risky"
        fix_plan["requires_approval"] = True

        state["_ssm_commands"] = validated.ssm_commands

        log_step(state["run_id"], "plan", "success",
                 f"Plan ready — {validated.action_type}, risk={validated.estimated_risk}")
        from agent.run_events import RUN_REGISTRY
        if state["run_id"] in RUN_REGISTRY:
            RUN_REGISTRY[state["run_id"]]["fix_plan"] = {
                "summary":     validated.summary,
                "action_type": validated.action_type,
                "steps":       validated.steps,
            }
        # ADD KARO — Force approval for demo
        validated.action_type      = "auto_risky"
        validated.requires_approval = True

        logger.info(f"[{state['run_id']}] Plan complete — action_type={validated.action_type}")

        return {
            "fix_plan":     fix_plan,
            "node_history": ["plan_node"],
            "errors":       [],
        }

    except Exception as e:
        logger.error(f"[{state['run_id']}] plan_node failed: {e}", exc_info=True)
        log_step(state["run_id"], "plan", "failed", f"Plan generation error: {str(e)[:100]}")
        return {
            "fix_plan":     _manual_only_plan(str(e)),
            "node_history": ["plan_node"],
            "errors":       [f"plan_node: {e}"],
        }


def _commands_look_risky(commands: list[str]) -> bool:
    risky_patterns = [
        "reboot", "shutdown", "poweroff", "init 0",
        "rm -rf", "dd if=", "mkfs", "> /dev/",
        "DROP TABLE", "DELETE FROM", "truncate",
        "iptables -F", "passwd", "chmod 777",
    ]
    command_text = " ".join(commands).lower()
    return any(pattern.lower() in command_text for pattern in risky_patterns)


def _manual_only_plan(reason: str) -> FixPlan:
    return {
        "summary":           "Manual investigation required",
        "steps":             ["1. Review CloudWatch logs", "2. SSH into affected instance", "3. Investigate manually"],
        "action_type":       "manual_only",
        "estimated_risk":    "high",
        "estimated_time":    "Unknown",
        "rollback_plan":     "No automated actions taken — nothing to roll back",
        "requires_approval": False,
    }
