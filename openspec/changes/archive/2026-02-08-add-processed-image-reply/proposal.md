## Why

The master-agent `/api/image` endpoint can return processed images (via Nano Banana Pro / Gemini 3 Pro Image) in the `processed_image_base64` field, but the telegram-bot currently ignores this field and always replies with text only. Users who send photos with processing prompts (e.g., "Remove the background") never receive the processed image back.

## What Changes

- Image handler checks `processed_image_base64` and `processed_image_mime_type` in the `/api/image` response
- When a processed image is present, bot replies with the image as a Telegram photo, using the text response as the caption
- When no processed image is present, bot replies with text as before (no behavior change)
- Caption is truncated to 1024 characters (Telegram photo caption limit)

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `image-handler`: Add requirement for handling `processed_image_base64` in API response — bot must send processed images back as photos instead of text-only replies

## Impact

- **Code**: `tgbot/handlers/image.py` — add processed image reply logic
- **Dependencies**: `base64`, `io` from stdlib; `telegram.InputFile` already available
- **APIs**: No API changes — only consuming existing response fields that were previously ignored
- **Tests**: Update/add tests for processed image reply path
