"""
api/routes/kubernetes.py
------------------------
GET /kubernetes  — Cluster node and pod status.

Currently returns mock data. To make it live, replace the mock
arrays with real kubectl/boto3 EKS API calls:

  import boto3
  eks = boto3.client("eks")
  eks.list_nodegroups(clusterName="cloudops-cluster-staging")

Or use the kubernetes Python client:
  pip install kubernetes
  from kubernetes import client, config
  config.load_incluster_config()  # inside EKS pod
  v1 = client.CoreV1Api()
  pods = v1.list_namespaced_pod(namespace="cloudops-staging")
"""

from fastapi import APIRouter

router = APIRouter(prefix="/kubernetes", tags=["kubernetes"])


@router.get("")
async def get_kubernetes():
    return {
        "nodes": [
            {
                "name":     "ip-10-0-1-42.ec2.internal",
                "status":   "Ready",
                "cpuUsed":  62,
                "memUsed":  71,
                "pods":     8,
            },
            {
                "name":     "ip-10-0-2-17.ec2.internal",
                "status":   "Ready",
                "cpuUsed":  38,
                "memUsed":  54,
                "pods":     6,
            },
        ],
        "pods": [
            {"name": "cloudops-agent-7c9d8f-x2k4p", "namespace": "cloudops-staging", "status": "Running",           "restarts": 0, "cpu": "120m", "memory": "340Mi", "age": "2d"},
            {"name": "cloudops-agent-7c9d8f-m8n2q", "namespace": "cloudops-staging", "status": "Running",           "restarts": 0, "cpu": "95m",  "memory": "310Mi", "age": "2d"},
            {"name": "ingest-worker-7c9",            "namespace": "cloudops-staging", "status": "CrashLoopBackOff",  "restarts": 4, "cpu": "0m",   "memory": "0Mi",   "age": "3h"},
            {"name": "rag-indexer-4f8a1",            "namespace": "cloudops-staging", "status": "Running",           "restarts": 1, "cpu": "210m", "memory": "512Mi", "age": "5d"},
            {"name": "otel-collector-9b3c",          "namespace": "observability",    "status": "Running",           "restarts": 0, "cpu": "40m",  "memory": "90Mi",  "age": "9d"},
        ],
    }
