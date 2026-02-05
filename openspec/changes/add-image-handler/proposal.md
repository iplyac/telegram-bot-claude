## Why

Users want to send images to the bot and get AI-powered analysis. Master-agent now supports `POST /api/image` endpoint for image processing with prompts. Telegram bot needs a handler to receive photo messages and forward them to this endpoint.

## What Changes

- Add photo message handler to receive images from Telegram
- Download image from Telegram servers and encode to base64
- Forward to master-agent `/api/image` endpoint with optional caption as prompt
- Return AI response to user
- Handle errors (backend unavailable, unsupported format, size limits)

## Capabilities

### New Capabilities

- `image-handler`: Telegram photo message handler that forwards images to master-agent for AI analysis

### Modified Capabilities

None - this is a new standalone handler similar to voice handler.

## Impact

- **Code**: `tgbot/handlers/image.py` - new handler module
- **Code**: `tgbot/dispatcher.py` - register photo message handler
- **Code**: `tgbot/services/backend_client.py` - add `forward_image` method
- **Dependencies**: Uses existing `BackendClient` with retry logic
- **APIs**: Consumes master-agent `/api/image` endpoint
