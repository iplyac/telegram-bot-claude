## Why

Users need a way to check their session status and debug conversation state directly from Telegram. Currently there's no visibility into whether a session exists or how many messages it contains.

## What Changes

- Add `/sessioninfo` command to telegram-bot
- Command calls master-agent's `/api/session-info` endpoint
- Display session information (conversation_id, session_id, existence status, message count)
- Handle error cases (backend unavailable, invalid response)

## Capabilities

### New Capabilities

- `sessioninfo-command`: Telegram command handler for `/sessioninfo` that queries master-agent and displays session information

### Modified Capabilities

None - this is a new standalone command that doesn't modify existing capabilities.

## Impact

- **Code**: `tgbot/dispatcher.py` - add new command handler
- **Code**: `tgbot/handlers/` - new handler module for sessioninfo
- **Dependencies**: Uses existing `BackendClient` or `httpx` for API calls
- **APIs**: Consumes master-agent `/api/session-info` endpoint (already exists)
