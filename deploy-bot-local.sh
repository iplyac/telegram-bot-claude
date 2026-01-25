#!/bin/bash
# Local development deployment script
# Uses native architecture (arm64 on Apple Silicon) for fast iteration

set -eo pipefail

IMAGE_NAME="telegram-bot-local"
CONTAINER_NAME="telegram-bot-local"

echo "=== Building Docker image (native architecture) ==="
docker build -t "$IMAGE_NAME" .

echo ""
echo "=== Stopping existing container (if any) ==="
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

echo ""
echo "=== Starting container ==="

# Build docker run command
DOCKER_CMD="docker run -d --name $CONTAINER_NAME -p 8080:8080"

# Add env file if exists
if [ -f .env ]; then
    echo "Using .env file"
    DOCKER_CMD="$DOCKER_CMD --env-file .env"
else
    echo "No .env file found, using environment defaults"
fi

DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME"

# Run container
eval $DOCKER_CMD

echo ""
echo "=== Container started ==="
echo "Container name: $CONTAINER_NAME"
echo "Port: 8080"
echo ""
echo "Health check: curl http://localhost:8080/healthz"
echo "Bot status:   curl http://localhost:8080/healthz/bot"
echo ""
echo "Logs: docker logs -f $CONTAINER_NAME"
echo "Stop: docker stop $CONTAINER_NAME"
