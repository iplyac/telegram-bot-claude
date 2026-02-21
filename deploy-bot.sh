#!/bin/bash
# Production deployment script using Google Cloud Build
# Recommended for Cloud Run deployments
#
# AGENT_API_URL Configuration:
# Set AGENT_API_URL to the public URL of master-agent before deploying:
#   AGENT_API_URL=https://master-agent-xxx.run.app ./deploy-bot.sh
#
# Without AGENT_API_URL, the bot will start but cannot forward messages.

set -euo pipefail

# Log to timestamped file
LOG_FILE="deploy-bot-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Deployment started at $(date) ==="
echo "Logging to: $LOG_FILE"

# Unset PORT to prevent accidental inclusion
unset PORT

# Required environment variables
: "${PROJECT_ID:=gen-lang-client-0741140892}"
: "${SERVICE_NAME:=telegram-bot}"
: "${REGION:=europe-west4}"

# Registry configuration
DOCKER_REGISTRY="${DOCKER_REGISTRY:-gcr.io}"

# Determine image base
if [[ "$DOCKER_REGISTRY" == *"pkg.dev" ]]; then
    # Artifact Registry
    : "${AR_REPO_NAME:?AR_REPO_NAME is required for Artifact Registry}"
    IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}"
else
    # Container Registry (default)
    IMAGE_BASE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
fi

# Git SHA for tagging
GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo '')}"

echo ""
echo "=== Configuration ==="
echo "PROJECT_ID:   $PROJECT_ID"
echo "SERVICE_NAME: $SERVICE_NAME"
echo "REGION:       $REGION"
echo "IMAGE_BASE:   $IMAGE_BASE"
echo "GIT_SHA:      ${GIT_SHA:-<not available>}"

# Compile-time default — override by setting AGENT_API_URL before running the script
AGENT_API_URL="${AGENT_API_URL:-https://master-agent-3qblthn7ba-ez.a.run.app}"
VPC_NETWORK="${VPC_NETWORK:-default}"
VPC_SUBNET="${VPC_SUBNET:-default}"

# Build environment variables string
ENV_VARS="LOG_LEVEL=${LOG_LEVEL:-INFO}"
ENV_VARS="${ENV_VARS},AGENT_API_URL=${AGENT_API_URL}"
echo "AGENT_API_URL: ${AGENT_API_URL}"

if [ -n "${TELEGRAM_WEBHOOK_URL:-}" ]; then
    ENV_VARS="${ENV_VARS},TELEGRAM_WEBHOOK_URL=${TELEGRAM_WEBHOOK_URL}"
fi

if [ -n "${TELEGRAM_WEBHOOK_PATH:-}" ]; then
    ENV_VARS="${ENV_VARS},TELEGRAM_WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH}"
fi

if [ -n "${TELEGRAM_WEBHOOK_SECRET:-}" ]; then
    ENV_VARS="${ENV_VARS},TELEGRAM_WEBHOOK_SECRET=${TELEGRAM_WEBHOOK_SECRET}"
fi

# Guard against PORT in ENV_VARS
if [[ "$ENV_VARS" == *"PORT"* ]]; then
    echo "ERROR: PORT is reserved by Cloud Run and must not be in ENV_VARS"
    exit 1
fi

echo ""
echo "=== Environment Variables ==="
echo "$ENV_VARS" | tr ',' '\n' | sed 's/=.*/=***/'

echo ""
echo "=== Building image with Cloud Build ==="
gcloud builds submit \
    --quiet \
    --tag "${IMAGE_BASE}:latest" \
    --project "$PROJECT_ID" \
    .

# Tag with Git SHA if available
if [ -n "$GIT_SHA" ]; then
    echo ""
    echo "=== Adding Git SHA tag ==="
    gcloud container images add-tag \
        --quiet \
        "${IMAGE_BASE}:latest" \
        "${IMAGE_BASE}:${GIT_SHA}" \
        --project "$PROJECT_ID"
fi

echo ""
echo "=== Deploying to Cloud Run ==="

gcloud run deploy "$SERVICE_NAME" \
    --quiet \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --image "${IMAGE_BASE}:latest" \
    --platform managed \
    --allow-unauthenticated \
    --network="${VPC_NETWORK}" \
    --subnet="${VPC_SUBNET}" \
    --vpc-egress=all-traffic \
    --set-env-vars "$ENV_VARS" \
    --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest"

echo ""
echo "=== Deployment complete ==="
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"

echo ""
echo "=== Granting bot SA invoker role on master-agent ==="
BOT_SA=$(gcloud run services describe "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format "value(spec.template.spec.serviceAccountName)")
MASTER_AGENT_SERVICE="${MASTER_AGENT_SERVICE:-master-agent}"
gcloud run services add-iam-policy-binding "$MASTER_AGENT_SERVICE" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --member="serviceAccount:${BOT_SA}" \
    --role=roles/run.invoker \
    --quiet
echo "Granted roles/run.invoker on ${MASTER_AGENT_SERVICE} to ${BOT_SA}"

echo ""
echo "=== Setting up Telegram webhook ==="

# Get bot token from Secret Manager
BOT_TOKEN=$(gcloud secrets versions access latest --secret=TELEGRAM_BOT_TOKEN --project="$PROJECT_ID" 2>/dev/null | grep -oE '[0-9]+:[A-Za-z0-9_-]+')

if [ -z "$BOT_TOKEN" ]; then
    echo "WARNING: Could not retrieve bot token from Secret Manager. Webhook not set."
else
    # Derive webhook secret from bot token (sha256, first 32 hex chars)
    WEBHOOK_SECRET=$(echo -n "$BOT_TOKEN" | sha256sum | cut -c1-32)

    # Webhook URL
    WEBHOOK_PATH="${TELEGRAM_WEBHOOK_PATH:-/telegram/webhook}"
    WEBHOOK_URL="${SERVICE_URL}${WEBHOOK_PATH}"

    echo "Webhook URL: $WEBHOOK_URL"

    # Set webhook with secret_token
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"${WEBHOOK_URL}\", \"secret_token\": \"${WEBHOOK_SECRET}\"}")

    if echo "$RESPONSE" | grep -q '"ok":true'; then
        echo "Webhook set successfully"
    else
        echo "WARNING: Failed to set webhook: $RESPONSE"
    fi
fi

echo ""
echo "=== Deployment finished at $(date) ==="
