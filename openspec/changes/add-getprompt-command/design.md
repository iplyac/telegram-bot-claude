## Context

Similar to `PromptReloadCommand`, we need a command to GET the current prompt. Master-agent exposes `GET /api/prompt` that returns `{"prompt": "...", "length": N}`.

## Goals / Non-Goals

**Goals:**
- Add `/getprompt` command following existing patterns
- Call master-agent `GET /api/prompt` endpoint
- Display prompt text (truncated if too long for Telegram)
- Show character count

**Non-Goals:**
- Prompt editing via Telegram
- Pagination for very long prompts

## Decisions

### 1. Command class structure

**Decision:** Create `GetPromptCommand` class extending `BaseCommand`

**Rationale:** Follows existing patterns.

### 2. Prompt truncation

**Decision:** Truncate prompt to 4000 characters with "..." if longer

**Rationale:** Telegram message limit is 4096 characters. Leave room for formatting.

### 3. Response format

**Decision:** Show prompt in code block with length info

**Rationale:** Code block preserves formatting. Length helps verify full prompt was retrieved.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Very long prompts | Truncate with clear indicator |
| Backend not configured | Check AGENT_API_URL, return clear message |
