## Why

Administrators need to reload the AI agent's system prompt at runtime without restarting the service. Master-agent now supports `POST /api/reload-prompt` endpoint that reloads the prompt from Vertex AI Prompt Management. A Telegram command is needed to trigger this.

## What Changes

- Add `/promptreload` command to telegram-bot
- Command calls master-agent's `/api/reload-prompt` endpoint
- Display success message with prompt length or error message
- Restrict command to admin users only (optional, based on config)

## Capabilities

### New Capabilities

- `promptreload-command`: Telegram command handler for `/promptreload` that triggers prompt reload on master-agent

### Modified Capabilities

None - this is a new standalone command.

## Impact

- **Code**: `tgbot/commands/promptreload.py` - new command handler
- **Code**: `tgbot/dispatcher.py` - register new command
- **APIs**: Consumes master-agent `/api/reload-prompt` endpoint
