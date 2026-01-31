# SPEC VERSION: ai-agent-v1
# STATUS: Production-Ready
# COMPATIBLE WITH: SPEC_tgbot_codex_v15.md
# TARGET PLATFORM: Google Cloud Run
# LAST UPDATED: 2026-01-27

---

## SYSTEM ROLE

You are a code-generation agent.
You MUST follow this SPEC exactly.
You MUST NOT make architectural decisions.
You MUST NOT ask questions.
If any requirement is ambiguous, you MUST FAIL.

---

## OUTPUT RULES

- Generate code only.
- Avoid explanations unless strictly necessary for correctness.
- Do NOT output prose outside code comments.
- Do NOT output markdown prose outside code comments.

---

## PROJECT

AI Agent Service for Google Cloud Run.
Compatible with Telegram Bot defined in SPEC_tgbot_codex_v15.md.

---

## PURPOSE

Implement a stateless, synchronous AI agent service that:
- Accepts user messages via HTTP
- Processes natural language input
- Returns text responses
- Integrates seamlessly with the Telegram bot

The agent MUST be able to start and operate even if MODEL_API_KEY is NOT configured.

---

## CLOUD RUN DEFAULT DEPLOYMENT CONTEXT (MANDATORY)

Unless explicitly overridden, the following values MUST be assumed:

- PROJECT_ID=gen-lang-client-0741140892
- SERVICE_NAME=ai-agent
- REGION=europe-west4

Rules:
- SERVICE_NAME and REGION MUST be documented verbatim in README.md
- PROJECT_ID MUST NOT be documented in README.md
- All values MAY be overridden via environment variables
- All deployment examples MUST use these defaults unless explicitly stated otherwise

---

## NON-GOALS

- No database
- No persistent memory
- No vector store
- No user profiles
- No background jobs
- No scheduling
- No infra-as-code
- No direct Telegram integration
- No authentication for /api/* endpoints (internal service usage)

---

## TECH STACK (FIXED / PINNED)

- Python 3.11
- fastapi==0.115.0
- uvicorn[standard]==0.32.0
- httpx==0.27.2
- google-cloud-secret-manager==2.20.2
- pytest==8.3.3
- pytest-asyncio==0.24.0
- python-json-logger==2.0.7
- google-generativeai==0.8.3
- Docker

---

## REQUIREMENTS.TXT (MANDATORY)

File: requirements.txt
MUST contain EXACT pinned versions:

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
google-cloud-secret-manager==2.20.2
pytest==8.3.3
pytest-asyncio==0.24.0
python-json-logger==2.0.7
google-generativeai==0.8.3
```

---

## REPOSITORY STRUCTURE (MANDATORY)

```
.
├── agent/
│   ├── __init__.py
│   ├── config.py
│   ├── llm_client.py
│   └── processor.py
├── secret_manager.py
├── app.py
├── requirements.txt
├── Dockerfile
├── deploy-agent.sh
├── deploy-agent-buildx.sh
├── deploy-agent-local.sh
├── README.md
├── .gitignore
├── .env.example
├── tests/
│   ├── test_health.py
│   ├── test_chat_api.py
│   └── test_llm_client.py
└── SPEC.ai-agent.v1.md
```

---

## PROCESS ARCHITECTURE (MANDATORY)

- Single Python process
- FastAPI (uvicorn) is the primary HTTP server listening on 0.0.0.0:$PORT
- Docker MUST start uvicorn only
- LLM client lifecycle MUST be managed via FastAPI lifespan startup/shutdown

---

## CONFIGURATION PRECEDENCE

1) Environment variables
2) Google Secret Manager
3) FAIL

---

## REQUIRED ENV VARS

- PORT (Cloud Run injects it; local default allowed)

---

## OPTIONAL ENV VARS

- MODEL_API_KEY
- MODEL_API_KEY_SECRET_ID
- MODEL_NAME
- MODEL_ENDPOINT
- GCP_PROJECT_ID
- PROJECT_ID
- REGION
- SERVICE_NAME
- LOG_LEVEL

---

## ENV NORMALIZATION (MANDATORY)

- project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID") or ""
- LOG_LEVEL defaults to "INFO" if missing
- MODEL_NAME defaults to "gemini-2.0-flash-exp" if missing

---

## SECRET MANAGER CONTRACT (MANDATORY)

- A secret named MODEL_API_KEY MAY exist in Google Secret Manager
- Secret version defaults to "latest"
- Secrets MUST NOT be logged
- Application code MUST NOT read any local secret files

---

## API KEY RESOLUTION ORDER (MANDATORY; in config.get_model_api_key)

1) If MODEL_API_KEY env var is set and non-empty → sanitize and use it
2) Else resolve secret_id = MODEL_API_KEY_SECRET_ID env var or default "MODEL_API_KEY"
3) Fetch secret_id:"latest" from Secret Manager, sanitize and use it
4) If still missing → return None (service starts without API key)

Key extraction and sanitization (MANDATORY):
- Extract key from formats: plain string, KEY=VALUE, or concatenated strings
- Use regex pattern to extract actual key value
- Apply sanitize_value() to remove whitespace and control characters
- Implement mask_token() for safe error logging

---

## CONFIGURATION MODULE (MANDATORY)

File: agent/config.py
- Stateless functions only
- MUST delegate Secret Manager calls to secret_manager.py

Required functions:
- get_port() -> int: returns int(PORT) or 8080 on missing/invalid
- get_project_id() -> str
- get_model_api_key() -> str | None (per API KEY RESOLUTION ORDER)
- get_model_name() -> str
- get_model_endpoint() -> str | None
- get_log_level() -> str
- get_region() -> str
- get_service_name() -> str

---

## LOGGING REQUIREMENTS (MANDATORY)

- MUST use Python logging module
- MUST log to stdout/stderr
- MUST emit structured JSON logs (one JSON object per line)
- MUST NOT log API keys or full message content (OK: session_id, message length)
- Log level controlled by LOG_LEVEL

---

## JSON LOG FORMAT (MANDATORY)

Each log line MUST be a single JSON object:

```json
{
  "timestamp": "<ISO-8601 with timezone>",
  "level": "DEBUG|INFO|WARNING|ERROR|CRITICAL",
  "logger": "<logger name>",
  "message": "<log message>",
  "logging.googleapis.com/trace": "<projects/{project_id}/traces/{trace_id}>",
  "extra": { ... }
}
```

---

## CLOUD TRACE INTEGRATION (MANDATORY)

- Extract trace header: X-Cloud-Trace-Context (format: TRACE_ID/SPAN_ID;o=...)
- trace_id = part before first "/"
- Store trace string in contextvars for current request context
- For each log entry produced inside a request, include field:
  logging.googleapis.com/trace = f"projects/{project_id}/traces/{trace_id}"
- If header missing or project_id empty → omit logging.googleapis.com/trace field

---

## FASTAPI ENDPOINTS (MANDATORY)

- GET /health -> HTTP 200, {"status":"ok"}
- GET /healthz -> HTTP 200, {"status":"ok"} (alias for Cloud Run)
- POST /api/chat -> PRIMARY ENDPOINT (see API CONTRACT)

---

## API CONTRACT (MANDATORY)

### POST /api/chat

Request JSON MUST be:
```json
{
  "session_id": "tg_<telegram_user_id>",
  "message": "<user_message_text>"
}
```

Response JSON MUST be:
```json
{
  "response": "<agent_reply_text>"
}
```

Rules:
- MUST return HTTP 200 on success
- MUST return Content-Type: application/json
- MUST complete within 30 seconds (matching bot timeout)
- MUST be safe to retry (stateless)
- On error: return HTTP 500 with {"error": "Agent unavailable, please try again later"}

---

## LLM CLIENT MODULE (MANDATORY)

File: agent/llm_client.py

Class: LLMClient

Constructor:
- __init__(self, api_key: str | None, model_name: str, endpoint: str | None)
- MUST create httpx.AsyncClient with timeout=25.0 (under bot 30s limit)
- MUST store api_key (can be None), model_name, endpoint

Method:
- async generate_response(self, message: str, session_id: str) -> str
  - If api_key is None → return "AI model not configured. Please contact administrator."
  - Call LLM API (Gemini or configured endpoint)
  - On success: return generated text response
  - On API error: raise RuntimeError with masked error (no API key in message)
  - MUST NOT log full message content or API key
  - MUST include timeout protection

Lifecycle:
- async close(self) -> None: await client.aclose()

---

## PROCESSOR MODULE (MANDATORY)

File: agent/processor.py

Class: MessageProcessor

Constructor:
- __init__(self, llm_client: LLMClient)

Method:
- async process(self, session_id: str, message: str) -> str
  - Validate input (non-empty message)
  - Call llm_client.generate_response(message, session_id)
  - Return response text
  - On any exception: raise with user-friendly message

---

## LLM CLIENT LIFECYCLE (MANDATORY)

- Create LLMClient in app.py lifespan startup
- Close LLMClient in lifespan shutdown before exiting

---

## LIFESPAN SEQUENCING (MANDATORY)

File: app.py MUST follow this sequence.

Startup (before yield):
1) Configure logging (first)
2) Resolve all config values (port, project_id, api_key, model_name, etc.)
3) Create LLMClient(api_key, model_name, endpoint)
4) Create MessageProcessor(llm_client)
5) Store llm_client and processor in app.state

yield  # FastAPI starts serving requests here

Shutdown (lifespan shutdown):
- await llm_client.close()
- Shutdown MUST complete within 8 seconds

---

## APP.PY STRUCTURE (MANDATORY)

File: app.py MUST contain:
- FastAPI app with @asynccontextmanager lifespan
- Middleware for Cloud Trace header extraction and contextvar propagation
- Routes for /health, /healthz, and /api/chat
- __main__ block for local run that starts uvicorn with timeout_graceful_shutdown=9

---

## DOCKERFILE (MANDATORY)

Mandatory first line:
```dockerfile
FROM --platform=linux/amd64 python:3.11-slim
```

- WORKDIR /app
- COPY requirements.txt + pip install
- COPY project files
- EXPOSE 8080
- CMD MUST be exactly:
  ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-graceful-shutdown 9"]

---

## PLATFORM STRATEGY (MANDATORY)

Overview:
- Local development on Apple Silicon MUST use native arm64
- Cloud Run deployment REQUIRES linux/amd64 images
- Python code and dependencies are platform-agnostic

Local Development (deploy-agent-local.sh):
- MUST NOT use --platform flag
- docker build MUST use native architecture
- docker run MUST use native architecture

Cloud Deployment (deploy-agent.sh):
- MUST build with Cloud Build (remote build)
- Cloud Run requires amd64 images

---

## DEPLOYMENT STRATEGY (MANDATORY)

Supported workflows:

1) Local Development (FAST, REQUIRED):
- Script: deploy-agent-local.sh
- Platform: Native (arm64 on Apple Silicon)
- Build: docker build (NO --platform flag)
- Run: docker run (NO --platform flag)

2) Production Deployment – OPTION A: Cloud Build (RECOMMENDED DEFAULT):
- Script: deploy-agent.sh
- Build location: Google Cloud Build (remote)
- Build command: gcloud builds submit
- Image architecture: linux/amd64 (handled by Cloud Build)

3) Production Deployment – OPTION B: Local Docker Buildx (ADVANCED):
- Script: deploy-agent-buildx.sh
- Build location: Local machine
- Build command: docker buildx build --platform linux/amd64 --push

---

## DEPLOYMENT SCRIPTS (MANDATORY)

### deploy-agent.sh

- MUST use gcloud builds submit (NOT local docker build)
- MUST be non-interactive
- MUST use: set -euo pipefail
- MUST require env vars: PROJECT_ID, SERVICE_NAME, REGION
- MUST create timestamped log: deploy-agent-$(date +%Y%m%d-%H%M%S).log
- MUST guard against PORT in env vars (unset PORT; check and fail if found)
- MUST support --no-cache flag for gcloud builds submit
- Registry selection:
  - Default DOCKER_REGISTRY="gcr.io"
  - If DOCKER_REGISTRY endswith "pkg.dev", AR_REPO_NAME is REQUIRED
- Image base:
  - If gcr.io: IMAGE_BASE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
  - Else: IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}"
- Tagging:
  - Always tag ${IMAGE_BASE}:latest
  - If GIT_SHA non-empty also tag ${IMAGE_BASE}:${GIT_SHA}
- GIT_SHA resolution:
  GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo '')}"
- Deploy:
  - MUST run gcloud run deploy with --quiet
  - MUST set env vars:
    PORT=8080 (error if already set)
    LOG_LEVEL=${LOG_LEVEL:-INFO}
    MODEL_NAME (only if set)
    MODEL_ENDPOINT (only if set)
  - MUST set secrets:
    --set-secrets "MODEL_API_KEY=MODEL_API_KEY:latest"

### deploy-agent-local.sh

- MUST be non-interactive
- MUST use: set -eo pipefail (DO NOT use -u)
- MUST docker build WITHOUT --platform flag
- MUST docker run WITHOUT --platform flag
- MUST map host 8080 to container 8080
- MUST pass --env-file .env ONLY if .env exists
- MUST NOT fail if .env missing

---

## GITIGNORE (MANDATORY)

File: .gitignore MUST include:
```
.env
.env.*
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.idea/
.vscode/
.DS_Store
deploy-agent-*.log
```

---

## .ENV.EXAMPLE (MANDATORY)

File: .env.example MUST include:

```bash
# Required
PORT=8080

# Model API key (use env for local dev; prod uses Secret Manager)
MODEL_API_KEY=your-api-key-here

# Model configuration (optional)
MODEL_NAME=gemini-2.0-flash-exp
# MODEL_ENDPOINT=https://custom-endpoint.com

# GCP context (optional)
# PROJECT_ID=your-gcp-project
# REGION=europe-west4
# SERVICE_NAME=ai-agent

# Logging (optional)
LOG_LEVEL=INFO
```

---

## README.md REQUIREMENTS (MANDATORY)

README.md MUST include sections with minimum content:

1) Overview:
- 2-3 sentences describing AI agent service
- Mention Cloud Run deployment
- State compatibility with Telegram bot

2) Architecture:
- Single process: uvicorn + FastAPI + LLM client
- Lifespan controls LLM client lifecycle
- Stateless request processing

3) Prerequisites:
- Docker
- gcloud (auth)
- Optional: Secret Manager + ADC for local secret reads
- LLM API key (Gemini or other)

4) Local development:
- cp .env.example .env
- set MODEL_API_KEY (or explain Secret Manager usage)
- ./deploy-agent-local.sh
- Verify: curl /health and POST to /api/chat

5) Cloud Run deployment:
- Store API key in Secret Manager (name MODEL_API_KEY)
- export PROJECT_ID SERVICE_NAME REGION
- ./deploy-agent.sh
- MUST warn against IDE terminals
- MUST include gcloud permission fix command:
  sudo chown -R $(whoami) ~/.config/gcloud

6) Security notes:
- Secrets not committed (.gitignore)
- Logs do not contain secrets/message bodies
- API key sanitization and masking

README MUST be <= 500 lines.

---

## TESTS (MANDATORY)

- Use pytest + pytest-asyncio
- Use unittest.mock (AsyncMock for async)
- Tests MUST be independent

### TEST FILE ORGANIZATION (MANDATORY)

tests/test_health.py:
- test_health_returns_ok: GET /health → 200 {"status":"ok"}
- test_healthz_returns_ok: GET /healthz → 200 {"status":"ok"}

tests/test_chat_api.py:
- test_chat_endpoint_valid_contract: POST /api/chat returns {"response": ...}
- test_chat_endpoint_missing_api_key: API key None → specific error response
- test_chat_endpoint_timeout: Mock timeout → 500 error
- test_chat_endpoint_invalid_json: Malformed request → 400/422 error

tests/test_llm_client.py:
- test_llm_client_no_api_key: Returns "not configured" message
- test_llm_client_success: Mock API call → returns response
- test_llm_client_api_error: Mock API error → raises with masked message

---

## EXECUTION PLAN (STRICT ORDER)

1. Create repository structure (all files, all __init__.py)
2. requirements.txt (pinned)
3. .gitignore
4. .env.example
5. secret_manager.py (reuse from bot if applicable, or create minimal version)
6. agent/config.py (with key extraction and sanitization)
7. logging setup (JSON + trace middleware in app.py)
8. agent/llm_client.py (with timeout, masking, error handling)
9. agent/processor.py
10. app.py (lifespan + routes + trace middleware)
11. Dockerfile (with --platform=linux/amd64)
12. deploy-agent-local.sh
13. deploy-agent.sh (Cloud Build, timestamped log, PORT guard)
14. deploy-agent-buildx.sh
15. README.md
16. tests
17. self-checks
18. STOP

---

## SELF-CHECKS (MANDATORY)

- Three deployment scripts exist: local, cloud-build, buildx
- deploy-agent.sh uses Cloud Build (gcloud builds submit)
- deploy-agent.sh creates timestamped log file
- deploy-agent.sh guards against PORT in environment
- deploy-agent-buildx.sh uses Docker Buildx with --platform linux/amd64
- deploy-agent-local.sh uses native architecture with NO --platform flag
- Dockerfile explicitly specifies --platform=linux/amd64
- All gcloud commands include --quiet flag
- API key extraction supports KEY=VALUE and plain formats
- API key sanitization removes whitespace and control characters
- Error messages mask API keys
- Trace header extracted and included in logs
- Service starts successfully without API key configured
- All tests pass
- No secrets logged
- README warns against IDE terminals
- README includes gcloud permission fix command

---

## DEFINITION OF DONE

- All SELF-CHECKS passed
- No violations of this SPEC detected
- Service integrates with Telegram bot without code changes
- Deployment mirrors bot deployment strategy

---

## STOP CONDITIONS

- STOP immediately after Definition of Done

---

END OF SPEC
