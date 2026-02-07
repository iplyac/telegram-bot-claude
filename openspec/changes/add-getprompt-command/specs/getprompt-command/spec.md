# GetPrompt Command

## Purpose

Telegram command `/getprompt` that retrieves and displays the current system prompt from master-agent.

## Interface

### Command Class

```python
class GetPromptCommand(BaseCommand):
    def __init__(self, agent_api_url: Optional[str]):
        self._agent_api_url = agent_api_url

    @property
    def name(self) -> str:
        return "getprompt"

    @property
    def description(self) -> str:
        return "Get the current AI agent system prompt"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Implementation
```

### API Integration

Calls master-agent endpoint:
- **Endpoint**: `GET /api/prompt`
- **Response**: `{"prompt": "...", "length": N}`

### Response Format

Success:
```
Current prompt (207 characters):

```
You are a helpful AI assistant...
```
```

Truncated (prompt > 4000 chars):
```
Current prompt (5432 characters, truncated):

```
You are a helpful AI assistant... (long text)...
```
```

Backend not configured:
```
Get prompt unavailable - backend not configured
```

Error:
```
Failed to get prompt: <error message>
```

## Behavior

1. Check if `agent_api_url` is configured
2. Make GET request to `/api/prompt`
3. Extract `prompt` and `length` from response
4. Truncate prompt to 4000 characters if needed
5. Format response with code block
6. Reply to user

## Registration

In `dispatcher.py`:
```python
from tgbot.commands.getprompt import GetPromptCommand

getprompt_cmd = GetPromptCommand(backend_client.agent_api_url)
application.add_handler(CommandHandler(getprompt_cmd.name, getprompt_cmd.handle))
```
