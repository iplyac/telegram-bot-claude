## Context

The telegram-bot has a command system using `BaseCommand` abstract class. Commands like `SessionInfoCommand` make HTTP requests to master-agent endpoints. Master-agent now exposes `POST /api/reload-prompt` that reloads the system prompt without restarting.

## Goals / Non-Goals

**Goals:**
- Add `/promptreload` command following existing patterns
- Call master-agent `/api/reload-prompt` endpoint
- Display result (success with prompt length, or error message)

**Non-Goals:**
- Admin-only restrictions (can be added later)
- Prompt editing via Telegram (out of scope)

## Decisions

### 1. Command class structure

**Decision:** Create `PromptReloadCommand` class extending `BaseCommand`

**Rationale:** Follows existing patterns (`SessionInfoCommand`, `TestCommand`).

### 2. HTTP client approach

**Decision:** Use direct `httpx` call (like `SessionInfoCommand`)

**Rationale:** Simple one-shot request, doesn't need `BackendClient` retry logic. The endpoint has no request body and returns a simple status.

### 3. Response handling

**Decision:** Parse JSON response and display appropriate message

**Rationale:**
- Success: "Prompt reloaded successfully (N characters)"
- Error from API: Show the error message from response
- HTTP error: "Failed to reload prompt"

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Backend not configured | Check AGENT_API_URL, return clear message |
| Endpoint returns error | Parse and display error from response |
| HTTP failure | Catch exception, return user-friendly message |
