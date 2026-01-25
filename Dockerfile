FROM --platform=linux/amd64 python:3.11-slim
# Build timestamp: 2026-01-25T19:50

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY secret_manager.py .
COPY app.py .
COPY tgbot/ ./tgbot/

# Expose port (documentation only, actual port set by Cloud Run)
EXPOSE 8080

# Start uvicorn with graceful shutdown
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-graceful-shutdown 9"]
