## Why

Administrators need to view the current system prompt that the AI agent is using. Master-agent exposes `GET /api/prompt` endpoint that returns the current prompt. A Telegram command is needed to retrieve and display it.

## What Changes

- Add `/getprompt` command to telegram-bot
- Command calls master-agent's `GET /api/prompt` endpoint
- Display the prompt text and character count
- Handle errors (backend unavailable, etc.)

## Capabilities

### New Capabilities

- `getprompt-command`: Telegram command handler for `/getprompt` that retrieves and displays the current system prompt

### Modified Capabilities

None - this is a new standalone command.

## Impact

- **Code**: `tgbot/commands/getprompt.py` - new command handler
- **Code**: `tgbot/dispatcher.py` - register new command
- **APIs**: Consumes master-agent `GET /api/prompt` endpoint
