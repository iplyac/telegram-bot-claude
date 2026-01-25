#!/bin/bash
# Production deployment script using Docker Buildx
# Alternative to Cloud Build, useful for debugging or restricted environments
# WARNING: Slower on Apple Silicon due to QEMU emulation

set -euo pipefail

# Log to timestamped file
LOG_FILE="deploy-bot-buildx-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Deployment (Buildx) started at $(date) ==="
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

echo ""
echo "=== Authenticating with Docker ==="
gcloud auth configure-docker --quiet

# Build environment variables string
ENV_VARS="LOG_LEVEL=${LOG_LEVEL:-INFO}"

if [ -n "${AGENT_API_URL:-}" ]; then
    ENV_VARS="${ENV_VARS},AGENT_API_URL=${AGENT_API_URL}"
fi

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
echo "=== Building and pushing image with Docker Buildx ==="
echo "WARNING: This may be slow on Apple Silicon due to QEMU emulation"

docker buildx build \
    --platform linux/amd64 \
    --push \
    -t "${IMAGE_BASE}:latest" \
    .

# Tag with Git SHA if available
if [ -n "$GIT_SHA" ]; then
    echo ""
    echo "=== Adding Git SHA tag ==="
    docker buildx build \
        --platform linux/amd64 \
        --push \
        -t "${IMAGE_BASE}:${GIT_SHA}" \
        .
fi

echo ""
echo "=== Deploying to Cloud Run ==="

if [ -n "$ENV_VARS" ]; then
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --image "${IMAGE_BASE}:latest" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "$ENV_VARS" \
        --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest"
else
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --image "${IMAGE_BASE}:latest" \
        --platform managed \
        --allow-unauthenticated \
        --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest"
fi

echo ""
echo "=== Deployment complete ==="
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format 'value(status.url)'

echo ""
echo "=== Deployment (Buildx) finished at $(date) ==="
