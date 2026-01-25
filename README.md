# Telegram Bot on Cloud Run

A Telegram bot with FastAPI backend designed for Google Cloud Run deployment. Supports both polling (development) and webhook (production) modes.

**Important:** Webhook mode is REQUIRED for production Cloud Run deployments. Polling mode is UNRELIABLE on Cloud Run due to instance scaling behavior.

## Architecture

- **Single process**: uvicorn + FastAPI + Telegram bot in one container
- **Lifespan management**: Bot lifecycle controlled via FastAPI lifespan events
- **Command pattern**: Modular command handlers in `tgbot/commands/`
- **Service layer**: Backend client and diagnostics in `tgbot/services/`

### Default Deployment Values

- `SERVICE_NAME`: telegram-bot
- `REGION`: europe-west4

## Prerequisites

- Docker
- Google Cloud SDK (`gcloud`) authenticated
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- (Optional) Google Secret Manager with Application Default Credentials for local secret reads

## Local Development

### Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your `TELEGRAM_BOT_TOKEN`:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

3. Build and run locally:
   ```bash
   ./deploy-bot-local.sh
   ```

4. Verify the bot is running:
   ```bash
   # Health check
   curl http://localhost:8080/healthz
   # Expected: {"status":"ok"}

   # Bot status
   curl http://localhost:8080/healthz/bot
   # Expected: {"bot_running":true,"mode":"polling","webhook_path":"/telegram/webhook"}
   ```

5. Test the bot in Telegram:
   - Send `/start` - should receive a greeting
   - Send `/test` - should receive instance info with hostname and timestamp

### Using Secret Manager Locally

If you have Google Cloud credentials configured, you can use Secret Manager instead of the `.env` file:

```bash
# Authenticate
gcloud auth application-default login

# Run without TELEGRAM_BOT_TOKEN in .env
# The bot will fetch the token from Secret Manager
```

## Cloud Run Deployment

### 1. Store Bot Token in Secret Manager

```bash
# Create the secret (first time only)
echo -n "YOUR_BOT_TOKEN" | gcloud secrets create TELEGRAM_BOT_TOKEN --data-file=-

# Or update existing secret
echo -n "YOUR_BOT_TOKEN" | gcloud secrets versions add TELEGRAM_BOT_TOKEN --data-file=-
```

**Note:** Secret Manager supports multi-line format with key=value pairs:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
OTHER_KEY=value
```

### 2. Deploy with Cloud Build (Recommended)

```bash
# Set required variables
export PROJECT_ID=your-project-id
export SERVICE_NAME=telegram-bot
export REGION=europe-west4

# Deploy
./deploy-bot.sh
```

### 3. Configure Webhook Mode (Required for Production)

After initial deployment, get the service URL and redeploy with webhook configuration:

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe telegram-bot --region europe-west4 --format 'value(status.url)')

# Redeploy with webhook
export TELEGRAM_WEBHOOK_URL=$SERVICE_URL
./deploy-bot.sh
```

### Alternative: Deploy with Docker Buildx

For debugging or environments without Cloud Build access:

```bash
./deploy-bot-buildx.sh
```

**Warning:** Buildx deployment is slower on Apple Silicon (M1/M2/M3/M4) due to QEMU emulation.

## Health Checks

| Endpoint | Method | Response |
|----------|--------|----------|
| `/healthz` | GET | `{"status":"ok"}` |
| `/healthz/bot` | GET | `{"bot_running":true,"mode":"polling\|webhook","webhook_path":"/telegram/webhook"}` |

Use these endpoints to verify deployment:

```bash
curl https://your-service-url/healthz
curl https://your-service-url/healthz/bot
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 8080 | Server port (managed by Cloud Run) |
| `TELEGRAM_BOT_TOKEN` | Yes* | - | Bot token (or use Secret Manager) |
| `TELEGRAM_BOT_TOKEN_SECRET_ID` | No | TELEGRAM_BOT_TOKEN | Secret Manager secret name |
| `TELEGRAM_WEBHOOK_URL` | No | - | Base URL for webhook mode |
| `TELEGRAM_WEBHOOK_PATH` | No | /telegram/webhook | Webhook endpoint path |
| `TELEGRAM_WEBHOOK_SECRET` | No | derived | Webhook validation secret |
| `AGENT_API_URL` | No | - | Backend API URL for message forwarding |
| `PROJECT_ID` | No | - | GCP project ID |
| `REGION` | No | europe-west4 | Cloud Run region |
| `SERVICE_NAME` | No | telegram-bot | Cloud Run service name |
| `LOG_LEVEL` | No | INFO | Logging level |

*Required via env var or Secret Manager

## Security

- **Secrets**: Never committed to git (`.gitignore`)
- **Webhook validation**: Uses Telegram's built-in `secret_token` header mechanism
- **Logging**: No secrets or message content in logs (only metadata like user_id, message length)
- **Sanitization**: All tokens and URLs are sanitized (whitespace and control characters removed)

## Troubleshooting

### "Code 3: Reserved env names provided: PORT"

This error occurs when trying to set `PORT` via `--set-env-vars`. Cloud Run reserves `PORT`.

**Solution:** The deployment scripts handle this automatically. If you see this error, ensure you're using the provided scripts without modifications.

### gcloud Permission Issues

If you encounter permission errors:

```bash
# Fix gcloud config permissions
sudo chown -R $(whoami) ~/.config/gcloud

# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### IDE Terminal Issues

IDE-integrated terminals (VS Code, PyCharm, Cursor) may isolate gcloud configuration.

**Solution:** Deploy from a system terminal:
- macOS: Terminal.app or iTerm2
- Windows: PowerShell or Command Prompt
- Linux: Native terminal

### Invalid Bot Token (404 Responses)

If webhook setup fails with 404:
- Verify your bot token is correct
- Check if the token was revoked in @BotFather
- Ensure no extra whitespace in the token

### Multi-line Secret Format

Secret Manager secrets can contain multiple key=value pairs. The bot extracts `TELEGRAM_BOT_TOKEN=` automatically. Ensure:
- No extra whitespace around the `=` sign
- Token value is on the same line as the key

### Webhook Not Working

1. Check bot status: `curl https://your-url/healthz/bot`
2. Verify webhook URL is HTTPS
3. Check Cloud Run logs for webhook setup errors
4. Ensure the service URL is publicly accessible

## Project Structure

```
.
├── tgbot/
│   ├── __init__.py
│   ├── telegram_bot.py      # Bot application factory
│   ├── dispatcher.py        # Handler registration
│   ├── config.py            # Configuration functions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── backend_client.py  # Backend API client
│   │   └── diagnostics.py     # Instance info
│   └── commands/
│       ├── __init__.py
│       ├── base.py          # Abstract base command
│       ├── start.py         # /start command
│       └── test.py          # /test command
├── secret_manager.py        # Secret Manager integration
├── app.py                   # FastAPI application
├── requirements.txt
├── Dockerfile
├── deploy-bot.sh            # Cloud Build deployment
├── deploy-bot-buildx.sh     # Docker Buildx deployment
├── deploy-bot-local.sh      # Local development
├── .env.example
├── .gitignore
├── .gcloudignore
└── tests/
    ├── test_health.py
    ├── test_chat_api.py
    ├── test_telegram_bot.py
    └── test_webhook_endpoint.py
```

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_health.py -v
```

## License

MIT
