# Telegram Bot Integration

## Session Info Endpoint

The `/api/session-info` endpoint allows you to query session information by conversation ID.

### Request

```http
POST /api/session-info
Content-Type: application/json

{
  "conversation_id": "tg_dm_234759359"
}
```

### Response

**Success (200):**
```json
{
  "conversation_id": "tg_dm_234759359",
  "session_id": "tg_dm_234759359",
  "session_exists": true,
  "message_count": 5
}
```

**Non-existing session (200):**
```json
{
  "conversation_id": "tg_dm_234759359",
  "session_id": "tg_dm_234759359",
  "session_exists": false,
  "message_count": null
}
```

**Missing conversation_id (400):**
```json
{
  "error": "1 validation error for SessionInfoRequest\nconversation_id\n  Field required..."
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | The conversation identifier (same as input) |
| `session_id` | string | The session identifier used by ADK (currently same as conversation_id) |
| `session_exists` | boolean | Whether the session exists in session storage |
| `message_count` | int \| null | Number of events in session (null if session doesn't exist or not supported) |

## Adding /sessioninfo Command to Telegram Bot

Add this handler to your telegram-bot to support the `/sessioninfo` command:

```python
import httpx
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

MASTER_AGENT_URL = "https://your-master-agent-url.run.app"


async def sessioninfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sessioninfo command - show current session info."""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # Build conversation_id using same format as chat messages
    if chat_type == "private":
        conversation_id = f"tg_dm_{chat_id}"
    else:
        conversation_id = f"tg_group_{chat_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{MASTER_AGENT_URL}/api/session-info",
                json={"conversation_id": conversation_id},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("session_exists"):
                message_count = data.get("message_count")
                count_str = f"\nMessages: {message_count}" if message_count is not None else ""
                text = f"Session info:\n- Conversation ID: `{data['conversation_id']}`\n- Session ID: `{data['session_id']}`\n- Status: Active{count_str}"
            else:
                text = f"No active session for this chat.\n- Conversation ID: `{conversation_id}`"

        except httpx.HTTPError as e:
            text = f"Failed to get session info: {e}"

    await update.message.reply_text(text, parse_mode="Markdown")


# Register the handler in your application setup:
# application.add_handler(CommandHandler("sessioninfo", sessioninfo_command))
```

### Notes

- The `conversation_id` format matches what telegram-bot already uses for chat/voice messages
- Sessions are stored in memory and do not persist across master-agent restarts
- The `message_count` reflects ADK events, not individual user messages
