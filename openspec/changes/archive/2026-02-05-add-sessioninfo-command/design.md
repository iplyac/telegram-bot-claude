## Context

The telegram-bot has a command system using `BaseCommand` abstract class with `name` property and `handle` method. Commands are registered in `dispatcher.py` via `CommandHandler`. The bot communicates with master-agent via `BackendClient` which provides retry logic for `/api/chat` and `/api/voice` endpoints.

Master-agent exposes a new `/api/session-info` endpoint that returns session metadata. We need to add a `/sessioninfo` command to telegram-bot that calls this endpoint.

## Goals / Non-Goals

**Goals:**
- Add `/sessioninfo` command following existing command patterns
- Query master-agent's `/api/session-info` endpoint
- Display session info in user-friendly format
- Handle errors gracefully (backend unavailable, invalid response)

**Non-Goals:**
- Modifying `BackendClient` retry logic (session-info is diagnostic, doesn't need retries)
- Adding session management capabilities (this is read-only)
- Supporting session info for other users (only current chat's session)

## Decisions

### 1. Create new command class vs inline handler

**Decision:** Create `SessionInfoCommand` class extending `BaseCommand`

**Rationale:** Follows existing patterns (`StartCommand`, `TestCommand`). Keeps code organized and testable.

**Alternative considered:** Inline handler in dispatcher - rejected for consistency.

### 2. Use BackendClient vs direct httpx

**Decision:** Use direct `httpx` call, not `BackendClient`

**Rationale:**
- `BackendClient._post_with_retry` expects `response` field in JSON, but `/api/session-info` returns different structure
- Session-info is diagnostic - retries add unnecessary complexity
- Single simple GET-like operation, not a conversation flow

**Alternative considered:** Add new method to `BackendClient` - rejected as over-engineering for a simple diagnostic command.

### 3. Conversation ID derivation

**Decision:** Derive `conversation_id` using same format as message handlers: `tg_dm_{chat_id}` for private, `tg_group_{chat_id}` for groups

**Rationale:** Must match the format used by `dispatcher.py` line 151-155 to query the correct session.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Backend URL not configured | Return clear error message "Session info unavailable - backend not configured" |
| Backend timeout/error | Catch `httpx.HTTPError`, return user-friendly message |
| Response format changes | Validate response structure, handle missing fields gracefully |
