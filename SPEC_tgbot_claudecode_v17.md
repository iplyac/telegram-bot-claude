# SPEC VERSION: ClaudeCode-v17 (based on v17)
# ADAPTED FOR: Claude Code (Agentic Coding Assistant)
# CHANGES FROM ORIGINAL v17:
# - Removed "SYSTEM ROLE" section (not applicable to Claude Code)
# - Removed "OUTPUT RULES" restrictions (Claude Code can explain and discuss)
# - Removed "MUST NOT ask questions" rule (Claude Code can clarify requirements)
# - Removed "If any requirement is ambiguous, you MUST FAIL" (Claude Code can discuss ambiguity)
# - Added CLAUDE CODE WORKFLOW section with best practices
# - Modified EXECUTION PLAN to support iterative development
# - Enhanced SELF-CHECKS to include code quality verification
# - Maintained all technical requirements from v17

# NEW IN v17:
# - Multi-line secret value extraction for TELEGRAM_BOT_TOKEN
# - Token/URL sanitization (strip whitespace and control characters)
# - Invalid token detection and logging for 404 responses from Telegram API
# - Webhook URL diagnostic logging (length, whitespace/control char counts, repr)
# - Webhook setup failure reason logging
# - Webhook receipt/parsing/queueing event logging
# - Strengthened requirement for webhook mode in production
# - Deployment script logging to timestamped log files
# - Enhanced IDE sandbox restrictions documentation
# - Explicit guard to fail deployment if ENV_VARS contains PORT
# - Clarified --project and --quiet on all gcloud commands
# - Enhanced readiness check documentation for /healthz and /healthz/bot

---

## CLAUDE CODE WORKFLOW (RECOMMENDED APPROACH)

Claude Code is an agentic coding assistant. Unlike strict code-generation agents, Claude Code:
- CAN ask clarifying questions when requirements are ambiguous
- CAN explain architectural decisions and trade-offs
- CAN discuss alternatives and suggest improvements
- SHOULD verify understanding before implementing large changes
- SHOULD explain complex implementations
- SHOULD highlight potential issues or risks

Recommended workflow:
1. Review specification thoroughly
2. Ask clarifying questions if needed
3. Confirm approach with user before major implementation
4. Implement iteratively (file by file or feature by feature)
5. Test and verify each component
6. Document decisions and rationale where helpful

---

PROJECT:
Telegram Bot + FastAPI on Google Cloud Run (single service).

PURPOSE:
Implement a Telegram bot that forwards user text messages to a FastAPI backend.
The bot MUST be able to start and operate even if AGENT_API_URL is NOT configured.


CLOUD RUN DEFAULT DEPLOYMENT CONTEXT (MANDATORY FOR THIS PROJECT):

Unless explicitly overridden, the following values MUST be assumed for Cloud Run deployment:

- PROJECT_ID=gen-lang-client-0741140892
- SERVICE_NAME=telegram-bot
- REGION=europe-west4

Rules:
- SERVICE_NAME and REGION MUST be documented verbatim in README.md.
- PROJECT_ID MUST NOT be documented in README.md.
- All values MAY be overridden via environment variables.
- All deployment examples MUST use these defaults unless explicitly stated otherwise.


NON-GOALS:
- No database
- No authentication for /api/* (except webhook secret header validation)
- No UI
- No infra-as-code

TECH STACK (FIXED / PINNED):
- Python 3.11
- python-telegram-bot==21.7
- fastapi==0.115.0
- uvicorn[standard]==0.32.0
- httpx==0.27.2
- google-cloud-secret-manager==2.20.2
- pytest==8.3.3
- pytest-asyncio==0.24.0
- python-json-logger==2.0.7
- Docker

REQUIREMENTS.TXT (MANDATORY):
File: requirements.txt
MUST contain EXACT pinned versions:
python-telegram-bot==21.7
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
google-cloud-secret-manager==2.20.2
pytest==8.3.3
pytest-asyncio==0.24.0
python-json-logger==2.0.7

REPOSITORY STRUCTURE (MANDATORY):
.
├── tgbot/
│   ├── __init__.py
│   ├── telegram_bot.py
│   ├── dispatcher.py
│   ├── config.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── backend_client.py
│   │   └── diagnostics.py
│   └── commands/
│       ├── __init__.py
│       ├── base.py
│       ├── start.py
│       └── test.py
├── secret_manager.py
├── app.py
├── requirements.txt
├── Dockerfile
├── deploy-bot.sh
├── deploy-bot-buildx.sh
├── deploy-bot-local.sh
├── README.md
├── .gitignore
├── .gcloudignore
├── .env.example
├── tests/
│   ├── test_health.py
│   ├── test_chat_api.py
│   ├── test_telegram_bot.py
│   └── test_webhook_endpoint.py
└── SPEC.tgbot.codex.v9.md

PROCESS ARCHITECTURE (MANDATORY):
- Single Python process.
- FastAPI (uvicorn) is the primary HTTP server listening on 0.0.0.0:$PORT.
- Telegram bot runs inside the same process.
- Docker MUST start uvicorn only (no separate bot process).
- Telegram bot lifecycle MUST be managed via FastAPI lifespan startup/shutdown.

CONFIGURATION PRECEDENCE:
1) Environment variables
2) Google Secret Manager
3) FAIL

REQUIRED ENV VARS:
- PORT (MANAGED BY CLOUD RUN). Strictly forbidden to set this via --set-env-vars in deployment scripts. Code must read it using os.getenv('PORT', '8080') for compatibility.

OPTIONAL ENV VARS:
- AGENT_API_URL
- TELEGRAM_BOT_TOKEN
- TELEGRAM_BOT_TOKEN_SECRET_ID
- TELEGRAM_WEBHOOK_URL
- TELEGRAM_WEBHOOK_PATH
- TELEGRAM_WEBHOOK_SECRET
- GCP_PROJECT_ID
- PROJECT_ID
- REGION
- SERVICE_NAME
- LOG_LEVEL

ENV NORMALIZATION (MANDATORY):
- project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID") or ""
- TELEGRAM_WEBHOOK_PATH defaults to "/telegram/webhook" if missing
- LOG_LEVEL defaults to "INFO" if missing
- Webhook mode is enabled iff TELEGRAM_WEBHOOK_URL is set and non-empty; otherwise polling mode.

SECRET MANAGER CONTRACT (MANDATORY):
- A secret named TELEGRAM_BOT_TOKEN ALREADY EXISTS in Google Secret Manager.
- Secret version defaults to "latest".
- Secrets MUST NOT be logged.
- Application code MUST NOT read any local secret files.
- Secrets MAY contain multi-line key/value pairs; token extraction MUST handle this.

SECRET VALUE EXTRACTION (MANDATORY):
Secret Manager secrets MAY be stored as multi-line text with key=value pairs.
Example secret content:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
OTHER_KEY=some_value
```

Extraction logic (in secret_manager.py):
1) Fetch raw secret payload string from Secret Manager.
2) Split payload into lines.
3) For each line:
   - Strip whitespace
   - If line starts with "TELEGRAM_BOT_TOKEN=", extract value after "="
   - If simple single-line format (no "="), use entire payload
4) Return extracted token value.

This logic MUST be implemented in secret_manager.py and used by config.get_bot_token().

TOKEN RESOLUTION ORDER (MANDATORY; in config.get_bot_token):
1) If TELEGRAM_BOT_TOKEN env var is set and non-empty → use it.
2) Else resolve secret_id = TELEGRAM_BOT_TOKEN_SECRET_ID env var or default "TELEGRAM_BOT_TOKEN".
3) Fetch secret_id:"latest" from Secret Manager and extract token value (per SECRET VALUE EXTRACTION).
4) If still missing → raise ValueError("TELEGRAM_BOT_TOKEN not found").

After obtaining token from any source, MUST sanitize it (see TOKEN SANITIZATION).

TOKEN SANITIZATION (MANDATORY):
All tokens and URLs obtained from environment variables or Secret Manager MUST be sanitized:
- Strip leading/trailing whitespace: token = token.strip()
- Remove control characters (ASCII 0-31, 127): token = ''.join(c for c in token if ord(c) > 31 and ord(c) != 127)
- Apply to: TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET, AGENT_API_URL

Implementation:
```python
def sanitize_value(value: str | None) -> str | None:
    if not value:
        return value
    value = value.strip()
    value = ''.join(c for c in value if ord(c) > 31 and ord(c) != 127)
    return value if value else None
```

This function MUST be in tgbot/config.py and applied to all sensitive configuration values.

WEBHOOK SECRET RESOLUTION (MANDATORY; in config.get_webhook_secret):
Goal: a stable secret across restarts (Cloud Run is stateless).
Resolution order:
1) If TELEGRAM_WEBHOOK_SECRET env var is set and non-empty → sanitize and use it.
2) Else derive deterministically from bot token:
   - secret = first 32 hex chars of sha256(TELEGRAM_BOT_TOKEN)
3) MUST return secret string (non-empty) or raise ValueError if bot token missing.
Notes:
- This derived secret is stable as long as bot token is stable (env or Secret Manager).
- MUST NOT log the secret.

CONFIGURATION MODULE (MANDATORY):
File: tgbot/config.py
- Stateless functions only.
- MUST delegate Secret Manager calls to secret_manager.py.
- MUST include sanitize_value() function.

Required functions:
- sanitize_value(value: str | None) -> str | None
- get_port() -> int: Returns int(os.getenv('PORT', '8080'))
- get_project_id() -> str
- get_bot_token() -> str  (per TOKEN RESOLUTION ORDER + sanitization)
- get_agent_api_url() -> str | None (with sanitization)
- get_webhook_url() -> str | None (with sanitization)
- get_webhook_path() -> str
- get_full_webhook_url() -> str | None: webhook_url.rstrip("/") + webhook_path
- get_webhook_secret() -> str (per WEBHOOK SECRET RESOLUTION + sanitization)
- get_log_level() -> str
- get_region() -> str
- get_service_name() -> str

LOGGING REQUIREMENTS (MANDATORY):
- MUST use Python logging module.
- MUST log to stdout/stderr.
- MUST emit structured JSON logs (one JSON object per line).
- MUST NOT log secrets or full inbound message text (OK: user_id, message length, update_id).
- Log level controlled by LOG_LEVEL.

JSON LOG FORMAT (MANDATORY):
Each log line MUST be a single JSON object:
{
  "timestamp": "<ISO-8601 with timezone>",
  "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
  "logger": "<logger name>",
  "message": "<log message>",
  "logging.googleapis.com/trace": "<projects/{project_id}/traces/{trace_id}>",
  "extra": { ... }
}

CLOUD TRACE INTEGRATION (MANDATORY):
- Extract trace header: X-Cloud-Trace-Context (format: TRACE_ID/SPAN_ID;o=...)
- trace_id = part before first "/"
- Store trace string in contextvars for current request context.
- For each log entry produced inside a request, include field:
  logging.googleapis.com/trace = f"projects/{project_id}/traces/{trace_id}"
- If header missing or project_id empty → omit logging.googleapis.com/trace field (do not include empty).

FASTAPI ENDPOINTS (MANDATORY):
- GET /healthz -> HTTP 200, {"status":"ok"}
- GET /healthz/bot -> HTTP 200 JSON:
  {"bot_running": bool, "mode": "polling"|"webhook", "webhook_path": str}
- POST /api/chat -> API CONTRACT below (stub echo service; used for contract tests)
- POST /api/image -> stub JSON response
- POST {TELEGRAM_WEBHOOK_PATH} -> webhook handler (only meaningful in webhook mode; safe to exist always)

API CONTRACT (MANDATORY):
POST /api/chat
Request JSON MUST be:
{
  "session_id": "tg_<telegram_user_id>",
  "message": "<user_message_text>"
}
Response JSON MUST be:
{
  "response": "<bot_reply_text>"
}
- MUST return HTTP 200.
- For this project, /api/chat MAY simply echo message like:
  response = f"echo: {message}"
  (This endpoint is separate from AGENT_API_URL forwarding. Bot forwarding uses AGENT_API_URL, not local /api/chat.)

POST /api/image (stub)
- MUST return HTTP 200 with JSON:
  {"status":"received","message":"Image processing not implemented"}

STANDARD USER MESSAGES (MANDATORY; verbatim):
- Configuration error: "AGENT_API_URL is not configured"
- Backend error: "Backend unavailable, please try again later."
- Unknown command: "Unknown command. Use /start for help."

TELEGRAM BOT DESIGN PATTERN (MANDATORY):
- Command pattern.
- One class per command.
- Common abstract base class in tgbot/commands/base.py.
- Each command implements: async handle(update, context) -> None.
- Command classes MUST NOT do HTTP directly.
- Command classes MUST NOT read env vars directly.

BOT MODULE STRUCTURE (MANDATORY):

File: tgbot/telegram_bot.py
Purpose:
- Create and configure telegram.ext.Application.
- Provide interface compatible with FastAPI lifespan.

Required functions:
- create_application(bot_token: str, update_queue_maxsize: int) -> Application:
  - MUST build Application with:
    Application.builder().token(bot_token).concurrent_updates(100).build()
  - MUST configure bounded update queue maxsize=update_queue_maxsize (100).
    Preferred implementation (PTB 21.7): builder.update_queue(asyncio.Queue(maxsize=...))
    If builder.update_queue is not available, MUST set application.update_queue = asyncio.Queue(maxsize=...)
  - MUST NOT start polling/webhook.
  - MUST NOT register handlers (dispatcher does it).
- async start_polling(application: Application) -> None:
  - MUST call await application.initialize()
  - MUST call await application.start()
  - MUST call await application.updater.start_polling() OR await application.run_polling()
  - MUST be usable as an asyncio Task (non-blocking from lifespan).
- async stop(application: Application) -> None:
  - MUST stop updater/bot and shutdown cleanly:
    await application.stop(); await application.shutdown()

File: tgbot/dispatcher.py
Purpose:
- Register handlers onto an existing Application instance.
Required function:
- setup_handlers(application, backend_client, diagnostics) -> None:
  - Register /start and /test commands
  - Register message handler for plain text messages
  - Register unknown command handler to send STANDARD USER MESSAGE for unknown commands
  - MUST wire dependencies so command handlers can call services (backend_client, diagnostics) without global state.

SERVICES:

BACKEND CLIENT SERVICE (MANDATORY):
File: tgbot/services/backend_client.py

Class: BackendClient
Constructor:
- __init__(self, agent_api_url: str | None)
- MUST create httpx.AsyncClient with timeout=30.0
- MUST store agent_api_url (can be None)

Retry policy (MANDATORY):
- Implement MANUAL retry loop (do NOT add new libraries).
- Max attempts: 3 total attempts.
- Backoff sleeps between attempts: 1s, 2s, 4s (i.e., sleep(2**attempt_index) where attempt_index starts at 0).
- Retry on:
  - httpx.ConnectError / httpx.ConnectTimeout / httpx.ReadTimeout
  - httpx.HTTPStatusError when response status is in {502, 503, 504}
- Do NOT retry on other 4xx/5xx.
- Total wall-clock time MUST remain <= 30 seconds (including sleeps). If the time budget would be exceeded, abort retries and raise.

Method:
- async forward_message(self, session_id: str, message: str) -> str
  - If agent_api_url is None → raise ValueError("AGENT_API_URL is not configured")
  - POST to f"{agent_api_url.rstrip('/')}/api/chat" with JSON per API CONTRACT
  - On success (HTTP 200): parse JSON and return field "response" as str
  - On invalid JSON or missing "response": raise ValueError
  - MUST NOT log full message content (OK: session_id, message length, status code)
  - MUST NOT swallow exceptions; raise after retries exhausted

Lifecycle:
- async close(self) -> None: await client.aclose()

BACKEND CLIENT LIFECYCLE (MANDATORY):
- Create BackendClient in app.py lifespan startup.
- Close BackendClient in lifespan shutdown before exiting.

DIAGNOSTICS SERVICE (MANDATORY):
File: tgbot/services/diagnostics.py

Function:
- get_instance_info(project_id: str, region: str, service_name: str) -> str
Behavior:
- Instance ID: socket.gethostname()
- Local time: datetime.now().astimezone().isoformat()
- MUST include timezone (tzinfo) in output
- MUST omit empty values for project/region/service_name
- MUST NOT expose secrets or dump env vars

TELEGRAM BOT BEHAVIOR (MANDATORY):
- Bot MUST start successfully even if AGENT_API_URL is missing.
- Bot MUST fail fast ONLY if bot token cannot be resolved.

Commands:
- /start: greeting message.
- /test: MUST output instance info + local time + timezone.

Text message handling:
- If AGENT_API_URL missing:
  - Reply with "AGENT_API_URL is not configured"
- If AGENT_API_URL present:
  - Call backend_client.forward_message(session_id, message)
  - Send returned response back to user
  - On any exception after retries: reply with "Backend unavailable, please try again later."

session_id:
- MUST be "tg_<telegram_user_id>"

WEBHOOK MODE (MANDATORY):
Mode selection:
- If TELEGRAM_WEBHOOK_URL is set → webhook mode.
- Else → polling mode.

Production requirement:
- README MUST state that webhook mode is REQUIRED for production Cloud Run deployments.
- README MUST state that polling mode is UNRELIABLE on Cloud Run.

Webhook security mechanism (MANDATORY):
- Use ONLY Telegram built-in secret_token header mechanism.
- When setting webhook, MUST call set_webhook(url=full_webhook_url, secret_token=webhook_secret).
- Webhook endpoint MUST validate request header:
  X-Telegram-Bot-Api-Secret-Token
- Validation:
  - If header missing OR not equal to webhook_secret → return HTTP 403.
  - MUST log WARNING (no secret value; OK: remote IP, user-agent, request id if any).
  - MUST NOT reveal secret in logs.

WEBHOOK DIAGNOSTIC LOGGING (MANDATORY):
Before calling set_webhook, log diagnostic information about the webhook URL:
- URL length
- Whitespace character count
- Control character count
- repr(url) for debugging

After set_webhook call:
- On success: log confirmation
- On failure:
  - Log failure reason
  - If response status is 404: log "Invalid bot token" hint
  - MUST NOT log secret values

Webhook endpoint implementation (MANDATORY):
Endpoint: POST {TELEGRAM_WEBHOOK_PATH}
- MUST log webhook receipt with update_id (if present in JSON)
- MUST accept raw JSON body.
- MUST quickly validate that JSON has "update_id" (int-like).
- MUST parse JSON into telegram.Update via telegram.Update.de_json(payload, bot) OR equivalent PTB method.
- MUST log successful parsing with update_id
- MUST access Application from app.state.tg_app.
- MUST enqueue update without blocking:
  - application.update_queue.put_nowait(update)
- MUST log successful queueing with update_id
- If QueueFull:
  - log ERROR with update_id
  - return HTTP 200
- MUST return HTTP 200 immediately (do not wait for processing).
- Any JSON parse errors or PTB parse errors:
  - log WARNING with error details
  - return HTTP 200
- Any other exceptions:
  - log ERROR with exception details
  - return HTTP 200
- MUST NOT expose processing errors to Telegram.

QUEUE PROTECTION (MANDATORY):
- update_queue MUST be bounded with maxsize=100.
- Use put_nowait + QueueFull handling in webhook endpoint.
- Application MUST be created with concurrent_updates=100 (limits processing concurrency).

LIFESPAN SEQUENCING (MANDATORY):
File: app.py MUST follow this sequence.

Startup (before yield):
1) Configure logging (first).
2) Resolve all config values (port, project_id, region, service_name, agent_api_url, webhook_url/path/secret).
3) Apply sanitization to all sensitive values.
4) Create BackendClient(agent_api_url).
5) Create Telegram Application (tg_app) via tgbot.telegram_bot.create_application(token, update_queue_maxsize=100).
6) Register handlers via tgbot.dispatcher.setup_handlers(...).
7) Store tg_app in app.state.tg_app.
8) Store webhook_secret in app.state.webhook_secret (for validation).
9) Determine mode:
   - If polling mode: start polling as an asyncio Task and store task in app.state.polling_task.
   - If webhook mode: DO NOT set webhook yet (server not ready). Store a flag app.state.webhook_mode=True.
yield  # FastAPI starts serving requests here

Post-yield (only for webhook mode):
10) Log webhook URL diagnostics (length, whitespace count, control char count, repr).
11) Call set_webhook on Telegram bot AFTER yield:
   - await tg_app.bot.set_webhook(url=full_webhook_url, secret_token=webhook_secret)
12) On success: log confirmation
13) If webhook setup fails:
   - log WARNING with failure reason
   - If status 404: log "Invalid bot token" hint
   - fallback to polling mode for this run:
     - start polling task and update app.state.mode accordingly
   - MUST NOT crash application

Shutdown (lifespan shutdown):
- If polling_task exists:
  - attempt graceful stop:
    - await tg_app.updater.stop() / tg_app.stop() as appropriate
  - await polling_task with timeout 7s; if timeout cancel
- Always:
  - await backend_client.close()
  - await tg_app.shutdown() (if initialized)
- Shutdown MUST complete within 8 seconds.

POLLING MODE IMPLEMENTATION (MANDATORY):
- Polling MUST run as an asyncio.Task.
- Use an async function that initializes + starts application and then runs polling loop.
- The polling task reference MUST be stored for shutdown.
- Do not block FastAPI startup.

APP.PY STRUCTURE (MANDATORY):
File: app.py MUST contain:
- FastAPI app with @asynccontextmanager lifespan.
- Middleware for Cloud Trace header extraction and contextvar propagation.
- Routes for /healthz, /healthz/bot, /api/chat, /api/image, and webhook path.
- Webhook endpoint MUST read app.state.webhook_secret and validate header.
- Webhook endpoint MUST log receipt, parsing, and queueing events.
- __main__ block for local run that starts uvicorn with timeout_graceful_shutdown=9.

DOCKERFILE (MANDATORY):
- Base image: python:3.11-slim
- First line MUST be: FROM --platform=linux/amd64 python:3.11-slim
- WORKDIR /app
- COPY requirements.txt + pip install
- COPY project files
- EXPOSE 8080
- CMD MUST be exactly:
  ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-graceful-shutdown 9"]


PLATFORM STRATEGY (MANDATORY):

Overview:
- Local development on Apple Silicon (M1/M2/M3/M4) MUST use native arm64.
- Cloud Run deployment REQUIRES linux/amd64 images.
- Python code and dependencies are platform-agnostic.

Local Development (deploy-bot-local.sh):
- MUST NOT use --platform flag.
- docker build MUST use native architecture (arm64 on Apple Silicon).
- docker run MUST use native architecture.
- Rationale: avoid QEMU x86_64 emulation which is 20–50% slower.
- Performance optimization is REQUIRED for iterative development.

Cloud Deployment (deploy-bot.sh):
- MUST build with: --platform linux/amd64 (via Cloud Build)
- Cloud Run will reject non-amd64 images.
- On Apple Silicon, Docker Desktop uses QEMU for amd64 builds.
- Slower builds are acceptable for deployment.

Verification:
- Local image architecture MUST be arm64:
  docker inspect telegram-bot-local --format='{{.Architecture}}'
- Deployed image architecture MUST be amd64.


DEPLOYMENT STRATEGY (MANDATORY):

Philosophy:
- Local development MUST prioritize speed and fast iteration.
- Production deployment MUST prioritize correctness, consistency, and Cloud Run compatibility.
- Apple Silicon (M1/M2/M3/M4) requires special handling to avoid slow emulation.

Supported workflows:

1) Local Development (FAST, REQUIRED):
- Script: deploy-bot-local.sh
- Platform: Native (arm64 on Apple Silicon, amd64 on Intel Macs)
- Build: docker build (NO --platform flag)
- Run: docker run (NO --platform flag)
- Purpose: Development, debugging, rapid iteration

2) Production Deployment – Cloud Build (RECOMMENDED):
- Script: deploy-bot.sh
- Build location: Google Cloud Build (remote)
- Build command: gcloud builds submit --tag
- Image architecture: linux/amd64 (handled by Cloud Build)
- Benefits:
  - Always correct architecture for Cloud Run
  - No local QEMU emulation on Apple Silicon
  - Faster and more consistent builds across team
  - Lower local CPU/battery usage
- Requirements:
  - Cloud Build API enabled
  - Internet access

3) Production Deployment – Local Docker Buildx (ADVANCED):
- Script: deploy-bot-buildx.sh
- Build location: Local machine
- Build command: docker buildx build --platform linux/amd64 --push
- Image architecture: linux/amd64
- Use cases:
  - Debugging Docker build issues
  - Custom Dockerfile experiments
  - Restricted environments without Cloud Build
- Drawbacks:
  - 2–3x slower on Apple Silicon due to QEMU emulation
  - High local CPU and battery usage

Default choice:
- SPEC MUST implement deploy-bot.sh using Cloud Build.
- SPEC MUST implement deploy-bot-buildx.sh as an alternative.
- README.md MUST document both approaches.
- Cloud Build MUST be presented as the recommended default.


DEPLOYMENT SCRIPTS (MANDATORY):

deploy-bot.sh:
- MUST use gcloud builds submit --tag (NOT local docker build).
- MUST be non-interactive.
- MUST use: set -euo pipefail
- MUST log to timestamped file: deploy-bot-$(date +%Y%m%d-%H%M%S).log
- MUST unset PORT before deployment.
- MUST require env vars: PROJECT_ID, SERVICE_NAME, REGION
- Registry selection:
  - Default DOCKER_REGISTRY="gcr.io"
  - If DOCKER_REGISTRY endswith "pkg.dev" (Artifact Registry), then AR_REPO_NAME is REQUIRED.
- Image base:
  - If DOCKER_REGISTRY == "gcr.io":
    IMAGE_BASE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
  - Else (Artifact Registry):
    IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}"
- Tagging:
  - Always tag ${IMAGE_BASE}:latest
  - If GIT_SHA non-empty also tag ${IMAGE_BASE}:${GIT_SHA}
- GIT_SHA resolution MUST be:
  GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo '')}"
- Build:
  - MUST use: gcloud builds submit --quiet --tag ${IMAGE_BASE}:latest --project "$PROJECT_ID" .
- Deploy:
  - Build ENV_VARS as single comma-separated string
  - Check if ENV_VARS contains "PORT" and FAIL if found
  - If ENV_VARS is empty, omit --set-env-vars flag entirely
  - MUST run gcloud run deploy with:
    --quiet
    --project "$PROJECT_ID"
    --image ${IMAGE_BASE}:latest
    --set-env-vars "$ENV_VARS" (only if ENV_VARS is non-empty)
  - MUST set env vars (when present):
    LOG_LEVEL=${LOG_LEVEL:-INFO}
    AGENT_API_URL (only if set)
    TELEGRAM_WEBHOOK_URL (only if set)
    TELEGRAM_WEBHOOK_PATH (only if set)
    TELEGRAM_WEBHOOK_SECRET (only if set)
  - MUST NOT set PORT (reserved by Cloud Run)
  - MUST NOT use eval for gcloud command
  - MUST set secrets:
    --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest"

Example implementation:
```bash
LOG_FILE="deploy-bot-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

unset PORT

ENV_VARS="LOG_LEVEL=${LOG_LEVEL:-INFO}"
if [ -n "${AGENT_API_URL:-}" ]; then
    ENV_VARS="${ENV_VARS},AGENT_API_URL=${AGENT_API_URL}"
fi

if [[ "$ENV_VARS" == *"PORT"* ]]; then
    echo "ERROR: PORT is reserved and must not be in ENV_VARS"
    exit 1
fi

gcloud builds submit --quiet --tag ${IMAGE_BASE}:latest --project "$PROJECT_ID" .

if [ -n "$ENV_VARS" ]; then
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        --image ${IMAGE_BASE}:latest \
        --set-env-vars "$ENV_VARS" \
        --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest" \
        ...
else
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        --image ${IMAGE_BASE}:latest \
        --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest" \
        ...
fi
```

deploy-bot-buildx.sh:
- MUST be non-interactive.
- MUST use: set -euo pipefail
- MUST docker buildx build with --platform linux/amd64 --push
- MUST follow same env var pattern as deploy-bot.sh (single string, no eval, no PORT)
- MUST log to timestamped file

deploy-bot-local.sh:
- MUST be non-interactive.
- MUST use: set -eo pipefail  (DO NOT use -u)
- MUST docker build WITHOUT --platform flag (native architecture).
- MUST docker run WITHOUT --platform flag.
- MUST map host 8080 to container 8080.
- MUST pass --env-file .env ONLY if .env exists.
- MUST NOT fail if .env missing.

.GCLOUDIGNORE (MANDATORY):
File: .gcloudignore
Purpose: Reduce Cloud Build context size and exclude unnecessary files

MUST include:
```
.git
.gitignore
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.env
.env.*
tests/
*.log
.DS_Store
.idea/
.vscode/
README.md
SPEC*.md
deploy-bot-*.log
```

GITIGNORE (MANDATORY):
File: .gitignore MUST include:
- .env
- .env.*
- __pycache__/
- *.pyc
- .pytest_cache/
- .venv/
- venv/
- .idea/
- .vscode/
- .DS_Store
- deploy-bot-*.log

.ENV.EXAMPLE (MANDATORY):
File: .env.example MUST include commented templates (no real secrets):
# Required
PORT=8080

# Telegram token (use env for local dev; prod uses Secret Manager)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Backend (optional)
# AGENT_API_URL=https://example.com

# Webhook mode (optional; leave empty for polling)
# TELEGRAM_WEBHOOK_URL=https://your-cloud-run-url
# TELEGRAM_WEBHOOK_PATH=/telegram/webhook
# TELEGRAM_WEBHOOK_SECRET=your-webhook-secret (recommended)

# GCP context (optional)
# PROJECT_ID=your-gcp-project
# REGION=us-central1
# SERVICE_NAME=telegram-bot

# Logging (optional)
LOG_LEVEL=INFO

README.md REQUIREMENTS (MANDATORY):
README.md MUST include sections with minimum content:
1) Overview:
- 2-3 sentences describing project and Cloud Run target.
- Mention polling + webhook.
- STATE: Webhook mode is REQUIRED for production Cloud Run deployments.
- STATE: Polling mode is UNRELIABLE on Cloud Run.

2) Architecture:
- Single process: uvicorn + FastAPI + bot.
- Lifespan controls bot start/stop.
- Command pattern + services separation.

3) Prerequisites:
- Docker
- gcloud (auth)
- Telegram token from @BotFather
- Optional: Secret Manager + ADC for local secret reads

4) Local development:
- cp .env.example .env
- set TELEGRAM_BOT_TOKEN (or explain Secret Manager usage)
- ./deploy-bot-local.sh
- Verify: send /test, /start
- Verify endpoints: curl /healthz and /healthz/bot

5) Cloud Run deployment:
- store token in Secret Manager (name TELEGRAM_BOT_TOKEN)
- export PROJECT_ID SERVICE_NAME REGION
- ./deploy-bot.sh
- MUST set TELEGRAM_WEBHOOK_URL to Cloud Run URL for production
- Redeploy to apply webhook configuration

6) Health checks:
- GET /healthz returns {"status":"ok"}
- GET /healthz/bot returns bot status and mode
- Use these endpoints to verify deployment

7) Security notes:
- secrets not committed (.gitignore)
- webhook header secret validation
- logs do not contain secrets/message bodies
- token/URL sanitization applied

8) Troubleshooting:
- "Code 3: Reserved env names provided: PORT" error
- gcloud permission issues
- IDE terminal vs system terminal
- Invalid bot token (404 responses)
- Webhook setup failures
- Multi-line secret format

README MUST be <= 500 lines.

TESTS (MANDATORY):
- Use pytest + pytest-asyncio.
- Use unittest.mock (AsyncMock for async).
- Tests MUST be independent.

TEST FILE ORGANIZATION (MANDATORY):

tests/test_health.py:
- test_healthz_returns_ok: GET /healthz → 200 {"status":"ok"}
- test_healthz_bot_reports_mode: GET /healthz/bot returns mode and webhook_path

tests/test_chat_api.py:
- test_chat_endpoint_valid_contract: POST /api/chat returns {"response": ...}
- test_image_endpoint_stub: POST /api/image returns stub JSON

tests/test_webhook_endpoint.py:
- test_webhook_rejects_missing_secret_header: no header -> 403
- test_webhook_rejects_wrong_secret_header: wrong header -> 403
- test_webhook_accepts_valid_secret_header: valid header -> 200
- test_webhook_invalid_json_returns_200: malformed JSON -> 200 (no crash)
- test_webhook_queue_full_returns_200: mock put_nowait to raise QueueFull -> 200 and logs ERROR
- test_webhook_enqueues_update: mock update_queue.put_nowait called once

tests/test_telegram_bot.py:
- test_start_command: /start -> greeting
- test_test_command_contains_hostname_and_time: /test contains hostname and ISO-like local time + timezone
- test_message_no_agent_url: reply is configuration error
- test_message_with_agent_url_success: BackendClient.forward_message mocked -> reply uses returned response
- test_message_with_agent_url_failure: BackendClient.forward_message raises -> reply backend error

EXECUTION PLAN (ITERATIVE DEVELOPMENT):

Note: Claude Code can implement this project iteratively.
The suggested order allows for testing and verification at each step.

Phase 1 - Foundation:
1. Create repository structure (all files, all __init__.py)
2. requirements.txt (pinned)
3. .gitignore
4. .gcloudignore
5. .env.example

Phase 2 - Secret Management & Configuration:
6. secret_manager.py (with multi-line extraction)
7. tgbot/config.py (with sanitize_value function)
8. logging setup (JSON + trace middleware)

Phase 3 - Services:
9. tgbot/services/diagnostics.py
10. tgbot/services/backend_client.py (manual retries)

Phase 4 - Bot Commands:
11. tgbot/commands/base.py
12. tgbot/commands/start.py
13. tgbot/commands/test.py
14. tgbot/dispatcher.py
15. tgbot/telegram_bot.py

Phase 5 - Application:
16. app.py (lifespan + routes + webhook validation + diagnostic logging + queue protection)

Phase 6 - Deployment:
17. Dockerfile (with --platform=linux/amd64)
18. deploy-bot-local.sh
19. deploy-bot.sh (using Cloud Build with logging and PORT guard)
20. deploy-bot-buildx.sh

Phase 7 - Documentation & Tests:
21. README.md (with webhook requirement and troubleshooting)
22. tests (all test files)

Phase 8 - Verification:
23. self-checks
24. code quality review
25. DONE

Alternative: Claude Code may implement in different order if user prefers, as long as all requirements are met.

SELF-CHECKS (MANDATORY):

Architecture & Platform:
- Three deployment scripts exist: local, cloud-build, buildx.
- Dockerfile first line is: FROM --platform=linux/amd64 python:3.11-slim
- deploy-bot.sh uses gcloud builds submit --tag (NOT local docker build).
- deploy-bot-buildx.sh uses Docker Buildx with --platform linux/amd64.
- deploy-bot-local.sh uses native architecture with NO --platform flag.
- .gcloudignore exists and excludes build artifacts.

Deployment Script Verification:
- deploy-bot.sh logs to timestamped file.
- deploy-bot.sh unsets PORT before deployment.
- deploy-bot.sh checks if ENV_VARS contains "PORT" and fails if found.
- deploy-bot.sh omits --set-env-vars if ENV_VARS is empty.
- deploy-bot.sh builds ENV_VARS as single comma-separated string.
- deploy-bot.sh uses direct gcloud call (NOT eval).
- deploy-bot-buildx.sh follows same pattern (single ENV_VARS, no eval, no PORT).
- All gcloud commands include --quiet and --project flags.
- Verified deployed image architecture is amd64.

Secret Management & Sanitization (v17):
- secret_manager.py extracts token from multi-line secrets.
- tgbot/config.py includes sanitize_value() function.
- All tokens/URLs are sanitized before use (TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET, AGENT_API_URL).

Webhook Diagnostic Logging (v17):
- Webhook URL diagnostic logging present (length, whitespace count, control char count, repr).
- Webhook setup failure logging includes reason.
- 404 response triggers "Invalid bot token" log hint.
- Webhook endpoint logs receipt with update_id.
- Webhook endpoint logs successful parsing with update_id.
- Webhook endpoint logs successful queueing with update_id.

Technical Requirements:
- No ambiguous behavior remains.
- Webhook uses ONLY header secret_token mechanism (no secret in path).
- Webhook secret is stable across restarts (env or sha256(bot token)).
- Webhook endpoint validates header and returns 403 on missing/wrong header.
- update_queue is bounded to maxsize=100 and QueueFull handled.
- BackendClient retries work (3 attempts, 1/2/4 backoff) for 502/503/504 + connect errors.
- Trace header extracted and included as logging.googleapis.com/trace when available.
- Polling + webhook modes both start without crashing.
- No secrets or full messages logged.

Code Quality (Claude Code additions):
- All Python code follows PEP 8 style guidelines.
- Type hints are used consistently.
- Docstrings are present for complex functions.
- Error handling is comprehensive and appropriate.
- Code is readable and maintainable.

Testing:
- All tests pass.
- Test coverage is adequate for critical paths.
- Tests are independent and don't share state.

Documentation:
- README is complete, accurate, and under 500 lines.
- README warns against IDE terminals for deployment.
- README includes gcloud permission fix command.
- README states webhook mode required for production.
- README states polling mode unreliable on Cloud Run.
- README documents /healthz and /healthz/bot endpoints.
- README includes troubleshooting for "Code 3: Reserved env names provided: PORT" error.
- README includes troubleshooting for invalid bot token (404 responses).
- README includes troubleshooting for multi-line secret format.

DEFINITION OF DONE:
- All SELF-CHECKS passed.
- No violations of this SPEC detected.
- User confirms implementation meets their needs.

---

## 🔐 DEPLOYMENT HARDENING (MANDATORY, v15 ADDITION, ENHANCED v17)

### 1) Cloud-Native Build Only (DEPLOY-BOT.SH)

Rationale:
- Local Docker builds on Apple Silicon (arm64) produce images incompatible with Cloud Run (amd64).
- Local Docker environments may suffer from DNS/SSL issues depending on IDE or OS configuration.
- Google Cloud Build guarantees correct architecture and stable networking.

Requirements:
- deploy-bot.sh MUST use Google Cloud Build.
- deploy-bot.sh MUST NOT use local docker build or docker push.
- Image build MUST be performed via gcloud builds submit.
- All gcloud commands MUST include --project and --quiet flags.
- Deployment MUST log to timestamped file for diagnosis.

Required command pattern:
```bash
LOG_FILE="deploy-bot-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

gcloud builds submit --quiet --tag ${IMAGE_BASE}:latest --project "$PROJECT_ID" .

gcloud run deploy $SERVICE_NAME \
  --quiet \
  --project "$PROJECT_ID" \
  --image ${IMAGE_BASE}:latest \
  [OTHER REQUIRED PARAMETERS]
```

### 2) Fixed Target Architecture (DOCKERFILE)

Rationale:
- Prevent accidental arm64 image builds when Docker is invoked locally.

Requirement:
- Dockerfile MUST explicitly target linux/amd64.

Mandatory Dockerfile first line:
```dockerfile
FROM --platform=linux/amd64 python:3.11-slim
```

### 3) gcloud Configuration Isolation (README / TROUBLESHOOTING)

Problem:
- IDE-integrated terminals may isolate gcloud config into project-local directories,
  breaking authentication, SSL certificates, and permissions.

Requirements:
- README MUST instruct users to deploy from a system terminal (Terminal.app, iTerm2),
  NOT from IDE-integrated terminals.
- README MUST include a troubleshooting command to fix gcloud permissions:

```bash
sudo chown -R $(whoami) ~/.config/gcloud
```

### 4) Non-Interactive Deployment (deploy-bot.sh)

Requirement:
- All gcloud commands in deploy-bot.sh MUST include the --quiet flag.
- All gcloud commands in deploy-bot.sh MUST include the --project flag.
- deploy-bot.sh MUST be fully non-interactive and safe for CI/CD usage.

### 5) PORT Reservation and Validation (deploy-bot.sh)

Requirements:
- PORT is RESERVED by Cloud Run and MUST NEVER be set via --set-env-vars.
- deploy-bot.sh MUST unset PORT before deployment.
- deploy-bot.sh MUST check if ENV_VARS contains "PORT" and FAIL immediately if found.
- If ENV_VARS is empty, --set-env-vars flag MUST be omitted entirely.

### 6) Secret Value Extraction and Sanitization (v17)

Requirements:
- Secret Manager secrets MAY contain multi-line key=value format.
- secret_manager.py MUST extract TELEGRAM_BOT_TOKEN value from multi-line secrets.
- All tokens and URLs MUST be sanitized (strip whitespace, remove control chars).
- tgbot/config.py MUST include sanitize_value() function and apply it to all sensitive values.

### 7) Webhook Diagnostic Logging (v17)

Requirements:
- Before calling set_webhook, log URL diagnostics (length, whitespace count, control char count, repr).
- On set_webhook failure, log the failure reason.
- If Telegram returns 404, log explicit "Invalid bot token" hint.
- Webhook endpoint MUST log receipt, parsing, and queueing events with update_id.

### 8) Production Webhook Requirement (v17)

Requirements:
- README MUST state that webhook mode is REQUIRED for production Cloud Run deployments.
- README MUST state that polling mode is UNRELIABLE on Cloud Run.
- Webhook mode MUST use service URL (no secrets in path).

---

## ❌ ANTI-PATTERNS (MUST AVOID)

### Deploy Script Anti-Patterns

**WRONG - Multiple --set-env-vars flags:**
```bash
# ❌ DO NOT DO THIS - causes conflicts
DEPLOY_CMD="gcloud run deploy ... --set-env-vars LOG_LEVEL=INFO"
DEPLOY_CMD="$DEPLOY_CMD --set-env-vars AGENT_API_URL=..."  # Multiple flags!
DEPLOY_CMD="$DEPLOY_CMD --set-env-vars WEBHOOK_URL=..."
eval $DEPLOY_CMD
```

**WRONG - Including PORT:**
```bash
# ❌ DO NOT DO THIS - PORT is reserved by Cloud Run
--set-env-vars PORT=8080,LOG_LEVEL=INFO
```

**WRONG - Using ENV in Dockerfile:**
```dockerfile
# ❌ DO NOT DO THIS - sets PORT permanently
ENV PORT=8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**WRONG - Not checking for PORT:**
```bash
# ❌ DO NOT DO THIS - silently includes PORT
ENV_VARS="PORT=8080,LOG_LEVEL=INFO"
gcloud run deploy --set-env-vars "$ENV_VARS"  # Will fail!
```

**CORRECT - Single comma-separated string with PORT guard:**
```bash
# ✅ CORRECT APPROACH
unset PORT  # Prevent accidental inclusion

ENV_VARS="LOG_LEVEL=${LOG_LEVEL:-INFO}"
if [ -n "${AGENT_API_URL:-}" ]; then
    ENV_VARS="${ENV_VARS},AGENT_API_URL=${AGENT_API_URL}"
fi

# Guard against PORT
if [[ "$ENV_VARS" == *"PORT"* ]]; then
    echo "ERROR: PORT is reserved and must not be in ENV_VARS"
    exit 1
fi

# Conditional deployment
if [ -n "$ENV_VARS" ]; then
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        --set-env-vars "$ENV_VARS" \
        ...
else
    gcloud run deploy "$SERVICE_NAME" \
        --quiet \
        --project "$PROJECT_ID" \
        ...  # No --set-env-vars
fi
```

**CORRECT - Dockerfile reads PORT from environment:**
```dockerfile
# ✅ CORRECT - reads from Cloud Run's injected PORT
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

### Why These Anti-Patterns Fail

1. **Multiple --set-env-vars flags**: gcloud CLI may not properly merge them
2. **eval command**: Introduces quoting/escaping issues and security risks  
3. **PORT in deployment**: Cloud Run reserves PORT and will reject the deployment with "Code 3: Reserved env names"
4. **ENV PORT in Dockerfile**: Hardcodes PORT, Cloud Run cannot override it
5. **No PORT validation**: Silent failures that waste debugging time

---

## 💡 CLAUDE CODE BEST PRACTICES

When implementing this specification:

1. **Communicate Progress**: Update user on which phase/component you're implementing
2. **Ask for Clarification**: If any requirement seems contradictory or unclear, ask before implementing
3. **Explain Complex Decisions**: When implementing complex parts (retry logic, sanitization, webhook diagnostics), briefly explain the approach
4. **Test Incrementally**: Suggest running tests after each major component
5. **Highlight Risks**: Point out potential issues or areas that need special attention
6. **Suggest Improvements**: If you see opportunities for better implementations that don't violate requirements, mention them
7. **Verify Understanding**: Confirm approach with user before implementing large or complex sections

Key areas requiring special attention in v17:
- Multi-line secret extraction logic
- Token/URL sanitization implementation
- Webhook diagnostic logging
- PORT guard in deployment script
- Timestamped logging for deployments

Remember: This is a collaborative coding process, not a strict code-generation pipeline. The goal is to produce high-quality, maintainable code that meets all requirements while ensuring the user understands the implementation.
