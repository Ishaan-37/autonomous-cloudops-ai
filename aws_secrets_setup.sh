#!/bin/bash
# aws_secrets_setup.sh
# --------------------
# Run once to bootstrap secrets in AWS Secrets Manager.
# Never store the actual values in this file — pass them as CLI args or from a password manager.

set -euo pipefail

ENV=${1:-staging}          # staging | production
REGION=${2:-us-east-1}
SECRET_NAME="cloudops-agent/$ENV/secrets"

echo "Creating secret: $SECRET_NAME in $REGION"

aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --region "$REGION" \
  --description "CloudOps Agent secrets for $ENV" \
  --secret-string '{
    "openai_api_key":       "sk-...",
    "pinecone_api_key":     "pcsk_...",
    "slack_bot_token":      "xoxb-...",
    "slack_signing_secret": "...",
    "langsmith_api_key":    "ls__..."
  }'

# Restrict access: only the agent's IRSA role can read this secret
aws secretsmanager put-resource-policy \
  --secret-id "$SECRET_NAME" \
  --resource-policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/cloudops-agent-irsa-role"
      },
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*"
    }]
  }'

echo "Secret created and policy applied."
echo "To update a secret value (e.g. after key rotation):"
echo "  aws secretsmanager put-secret-value --secret-id $SECRET_NAME --secret-string '{...}'"
