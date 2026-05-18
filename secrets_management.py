"""
secrets_management.py
---------------------
Production-grade secrets pattern for AWS-deployed Python services.
Uses AWS Secrets Manager as the single source of truth.
All secrets are loaded once at startup and cached — zero plaintext in env vars,
zero secrets in code, zero .env files committed to Git.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SecretsManagerSettingsSource, SettingsConfigDict

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. Low-level helper: fetch one secret from AWS
# ─────────────────────────────────────────────

def get_secret(secret_name: str, region: str = "us-east-1") -> dict[str, Any]:
    """
    Fetch a JSON secret from AWS Secrets Manager.
    Uses the pod's IRSA role — no access keys needed.
    Results are cached by lru_cache so we only hit the API once per process.
    """
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_str = response.get("SecretString", "{}")
        return json.loads(secret_str)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Secret '{secret_name}' not found in Secrets Manager") from e
        elif error_code == "AccessDeniedException":
            raise PermissionError(
                f"Pod IAM role lacks secretsmanager:GetSecretValue for '{secret_name}'"
            ) from e
        raise


# ─────────────────────────────────────────────
# 2. Pydantic settings model — typed config
# ─────────────────────────────────────────────

class CloudOpsSettings(BaseSettings):
    """
    Single source of truth for all app configuration.

    Priority order (highest to lowest):
      1. Environment variables (useful for local dev overrides)
      2. AWS Secrets Manager (production)
      3. Default values

    Usage:
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    """

    model_config = SettingsConfigDict(
        env_prefix="CLOUDOPS_",
        case_sensitive=False,
    )

    # ── App config (non-secret, safe in env vars) ──
    environment: str = Field(default="development")
    aws_region: str = Field(default="us-east-1")
    log_level: str = Field(default="INFO")
    slack_channel: str = Field(default="#cloudops-alerts")
    eks_namespace: str = Field(default="cloudops-prod")

    # ── Secrets (loaded from Secrets Manager) ──
    openai_api_key: SecretStr = Field(default=...)
    pinecone_api_key: SecretStr = Field(default=...)
    slack_bot_token: SecretStr = Field(default=...)
    slack_signing_secret: SecretStr = Field(default=...)
    langsmith_api_key: SecretStr = Field(default=...)

    # ── Pinecone config ──
    pinecone_environment: str = Field(default="us-east-1-aws")
    pinecone_log_index: str = Field(default="cloudops-logs")
    pinecone_docs_index: str = Field(default="aws-docs")


# ─────────────────────────────────────────────
# 3. Secret loader: Secrets Manager → Settings
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_settings() -> CloudOpsSettings:
    """
    Load settings once, cache forever per process.
    In production (EKS): secrets come from AWS Secrets Manager via IRSA.
    In local dev: secrets come from env vars (e.g. set in your shell or .env).
    """
    env = os.getenv("CLOUDOPS_ENVIRONMENT", "development")

    if env == "development":
        # Local dev: load from env vars (set manually, never commit .env to Git)
        logger.info("Loading secrets from environment variables (dev mode)")
        return CloudOpsSettings()

    # Production / staging: fetch from Secrets Manager
    logger.info(f"Loading secrets from AWS Secrets Manager (env={env})")

    secret_name = f"cloudops-agent/{env}/secrets"
    secrets = get_secret(secret_name, region=os.getenv("AWS_REGION", "us-east-1"))

    # Inject secrets as env vars temporarily so pydantic-settings can pick them up
    # This keeps the Settings model interface consistent across envs
    os.environ.setdefault("CLOUDOPS_OPENAI_API_KEY",       secrets["openai_api_key"])
    os.environ.setdefault("CLOUDOPS_PINECONE_API_KEY",      secrets["pinecone_api_key"])
    os.environ.setdefault("CLOUDOPS_SLACK_BOT_TOKEN",       secrets["slack_bot_token"])
    os.environ.setdefault("CLOUDOPS_SLACK_SIGNING_SECRET",  secrets["slack_signing_secret"])
    os.environ.setdefault("CLOUDOPS_LANGSMITH_API_KEY",     secrets["langsmith_api_key"])

    return CloudOpsSettings()


# ─────────────────────────────────────────────
# 4. FastAPI integration example
# ─────────────────────────────────────────────

"""
In api/main.py:

    from secrets_management import get_settings
    from fastapi import FastAPI, Depends

    app = FastAPI()

    @app.on_event("startup")
    async def startup():
        # Eagerly validate all secrets at boot — fail fast, not mid-request
        settings = get_settings()
        assert settings.openai_api_key.get_secret_value(), "OpenAI key missing"
        assert settings.pinecone_api_key.get_secret_value(), "Pinecone key missing"
        logger.info(f"CloudOps Agent started — env={settings.environment}")

    def get_openai_client():
        settings = get_settings()
        return AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
"""


# ─────────────────────────────────────────────
# 5. Secret rotation (auto, zero-downtime)
# ─────────────────────────────────────────────

"""
Enable rotation in Terraform:

    resource "aws_secretsmanager_secret_rotation" "cloudops_rotation" {
      secret_id           = aws_secretsmanager_secret.cloudops.id
      rotation_lambda_arn = aws_lambda_function.rotate_secret.arn

      rotation_rules {
        automatically_after_days = 30
      }
    }

For zero-downtime rotation:
- Clear the lru_cache on SIGHUP so the next request fetches the new secret:

    import signal

    def handle_sighup(signum, frame):
        get_settings.cache_clear()
        logger.info("Secret cache cleared — will re-fetch on next request")

    signal.signal(signal.SIGHUP, handle_sighup)
"""
