"""
api/routes/costs.py
-------------------
GET /costs  — AWS spend data and FinOps savings opportunities.

Currently returns mock data. To make it live, wire in AWS Cost Explorer:

  import boto3
  ce = boto3.client("ce", region_name="us-east-1")
  response = ce.get_cost_and_usage(
      TimePeriod={"Start": "2026-07-01", "End": "2026-07-31"},
      Granularity="DAILY",
      Metrics=["UnblendedCost"],
      GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
  )

Cost Explorer API has no extra charge beyond standard AWS costs.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("")
async def get_costs():
    return {
        "costTrend": [
            {"day": "Mon", "spend": 118},
            {"day": "Tue", "spend": 124},
            {"day": "Wed", "spend": 119},
            {"day": "Thu", "spend": 142},
            {"day": "Fri", "spend": 131},
            {"day": "Sat", "spend": 96},
            {"day": "Sun", "spend": 109},
        ],
        "costByService": [
            {"service": "EKS",        "cost": 1840, "color": "#4FD1C5"},
            {"service": "EC2",        "cost": 980,  "color": "#FF8A3D"},
            {"service": "S3",         "cost": 320,  "color": "#8A96A6"},
            {"service": "CloudWatch", "cost": 410,  "color": "#5B6675"},
            {"service": "Other",      "cost": 270,  "color": "#2A3441"},
        ],
        "savingsOpportunities": [
            {"id": 1, "resource": "vol-0e5f6a7b8c9d0e1f", "type": "Unattached EBS volume",        "monthlySavings": 18.40, "status": "flagged"},
            {"id": 2, "resource": "i-0b2c3d4e5f6a7b8c",   "type": "Idle EC2 instance (t3.large)", "monthlySavings": 84.30, "status": "flagged"},
            {"id": 3, "resource": "snap-0a1b2c3d4e5f6789", "type": "Orphaned snapshot",             "monthlySavings": 6.20,  "status": "resolved"},
            {"id": 4, "resource": "nat-0f9e8d7c6b5a4321",  "type": "Unused NAT gateway",           "monthlySavings": 32.40, "status": "flagged"},
            {"id": 5, "resource": "lb-0123456789abcdef",   "type": "Idle load balancer",            "monthlySavings": 21.90, "status": "flagged"},
        ],
    }
