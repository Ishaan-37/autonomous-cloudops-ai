from dotenv import load_dotenv
load_dotenv()

import json
import logging
import os
from typing import Optional

from groq import AsyncGroq
from pydantic import BaseModel, Field, validator

from agent.state import AgentState, RootCauseAnalysis
from agent.run_events import log_step

logger = logging.getLogger(__name__)
oai = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

RCA_SYSTEM_PROMPT = """
You are a Senior Site Reliability Engineer (SRE) at a cloud-native company.
You are part of an autonomous CloudOps AI agent that monitors AWS infrastructure.

YOUR JOB:
Analyze the CloudWatch alarm and log context provided, then identify the ROOT CAUSE.
Be specific, concise, and actionable.

RULES:
1. NEVER invent or hallucinate resource IDs, instance IDs, or IP addresses.
2. If uncertain, set confidence below 0.6.
3. Be specific — "memory leak in payment-service causing OOM kills" is good.
4. Severity rules:
   - CRITICAL: service is DOWN or data loss risk
   - HIGH: service degraded, users impacted
   - MEDIUM: performance degradation, no user impact yet
   - LOW: warning threshold, no immediate action needed

YOU MUST RESPOND WITH ONLY THIS JSON OBJECT — NO OTHER TEXT:
{
  "root_cause": "Clear explanation of what caused the issue",
  "confidence": 0.85,
  "severity": "HIGH",
  "category": "cpu",
  "affected_resources": [],
  "symptoms": ["symptom 1", "symptom 2"],
  "contributing_factors": ["factor 1", "factor 2"]
}

CATEGORIES: memory | cpu | disk | network | application | database | cost | unknown
""".strip()


class RCAOutput(BaseModel):
    root_cause:           str
    confidence:           float = Field(ge=0.0, le=1.0)
    severity:             str
    category:             str
    affected_resources:   list[str] = []
    symptoms:             list[str] = []
    contributing_factors: list[str] = []

    @validator("severity")
    def validate_severity(cls, v):
        allowed = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        v = v.upper()
        return v if v in allowed else "MEDIUM"

    @validator("category")
    def validate_category(cls, v):
        allowed = {"memory", "cpu", "disk", "network", "application",
                   "database", "cost", "unknown"}
        v = v.lower()
        return v if v in allowed else "unknown"

    @validator("confidence")
    def clamp_confidence(cls, v):
        return max(0.0, min(1.0, v))


async def analyze_node(state: AgentState) -> dict:
    logger.info(f"[{state['run_id']}] analyze_node started")
    log_step(state["run_id"], "analyze", "running", "Groq LLM analyzing root cause...")

    alert       = state["alert"]
    log_context = state.get("log_context", "No logs available")
    doc_context = state.get("doc_context", "No documentation available")

    user_message = f"""
CLOUDWATCH ALARM DETAILS:
{json.dumps(alert, indent=2)}

ALARM DESCRIPTION:
Name:   {alert.get('AlarmName', 'Unknown')}
Reason: {alert.get('StateReason', 'Unknown')}
State:  {alert.get('NewStateValue', 'ALARM')}
Region: {alert.get('Region', 'us-east-1')}

{log_context}

{doc_context}

Analyze the above alarm and identify the root cause.
Respond with ONLY a valid JSON object. No explanation, no markdown, just JSON.
""".strip()

    try:
        response = await oai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": RCA_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        raw_json = response.choices[0].message.content.strip()
        logger.info(f"[{state['run_id']}] Raw response: {raw_json[:200]}")
        # Remove <think>...</think> tags (qwen reasoning mode)
        if "<think>" in raw_json:
            if "</think>" in raw_json:
                raw_json = raw_json.split("</think>")[-1].strip()

        # Clean markdown fences if model wraps in ```json
        if "```" in raw_json:
            parts = raw_json.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw_json = part
                    break

        rca_data  = json.loads(raw_json)
        validated = RCAOutput(**rca_data)

        root_cause: RootCauseAnalysis = {
            "root_cause":           validated.root_cause,
            "confidence":           validated.confidence,
            "severity":             validated.severity,
            "category":             validated.category,
            "affected_resources":   validated.affected_resources,
            "symptoms":             validated.symptoms,
            "contributing_factors": validated.contributing_factors,
        }

        log_step(state["run_id"], "analyze", "success",
                 f"RCA complete — {validated.severity}, {validated.confidence:.0%} confidence")
        from agent.run_events import RUN_REGISTRY
        if state["run_id"] in RUN_REGISTRY:
            RUN_REGISTRY[state["run_id"]]["root_cause"] = validated.root_cause
            RUN_REGISTRY[state["run_id"]]["fix_plan"]   = None  # plan_node fill karega


        logger.info(f"[{state['run_id']}] RCA complete — severity={validated.severity}")

        return {
            "root_cause":   root_cause,
            "node_history": ["analyze_node"],
            "errors":       [],
        }

    except json.JSONDecodeError as e:
        logger.error(f"[{state['run_id']}] JSON parse error: {e}")
        log_step(state["run_id"], "analyze", "failed", f"JSON parse error: {e}")
        return {
            "root_cause":   _fallback_rca(alert, str(e)),
            "node_history": ["analyze_node"],
            "errors":       [f"analyze_node: JSON parse error — {e}"],
        }

    except Exception as e:
        logger.error(f"[{state['run_id']}] analyze_node failed: {e}", exc_info=True)
        log_step(state["run_id"], "analyze", "failed", f"LLM error: {str(e)[:100]}")
        return {
            "root_cause":   _fallback_rca(alert, str(e)),
            "node_history": ["analyze_node"],
            "errors":       [f"analyze_node: {e}"],
        }


def _fallback_rca(alert: dict, error: str) -> RootCauseAnalysis:
    return {
        "root_cause":           f"Analysis failed — manual review required. Alarm: {alert.get('AlarmName')}",
        "confidence":           0.0,
        "severity":             "HIGH",
        "category":             "unknown",
        "affected_resources":   [],
        "symptoms":             [alert.get("StateReason", "Unknown")],
        "contributing_factors": [f"LLM error: {error}"],
    }
