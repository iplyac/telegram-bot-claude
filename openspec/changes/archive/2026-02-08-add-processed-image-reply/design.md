## Context

The master-agent `/api/image` endpoint already returns `processed_image_base64` and `processed_image_mime_type` fields when an image is processed by Nano Banana Pro (Gemini 3 Pro Image). The telegram-bot `image.py` handler currently ignores these fields and always replies with `reply_text()`. The `BackendClient.forward_image()` already returns the full response dict including these fields — no backend changes needed.

## Goals / Non-Goals

**Goals:**
- Reply with processed images as Telegram photos when `processed_image_base64` is present in the response
- Use the text response as photo caption (truncated to Telegram's 1024 char limit)
- Fall back to text reply when no processed image is returned (preserve existing behavior)

**Non-Goals:**
- Changing the `/api/image` request payload or backend logic
- Supporting document or video responses
- Adding new Telegram commands

## Decisions

### Decision 1: Inline reply logic in image handler

Add the processed image check directly in `handle_photo_message()` after receiving the backend response. No new abstractions needed — it's a single if/else branch.

**Rationale**: The logic is simple (check field, decode base64, send photo). A helper or separate module would be over-engineering for ~10 lines of code.

### Decision 2: Use `reply_photo` with `InputFile` from bytes

Decode `processed_image_base64` to bytes, wrap in `io.BytesIO`, and send via `update.message.reply_photo(photo=InputFile(...))`.

**Rationale**: This is the standard python-telegram-bot approach. `InputFile` accepts `BytesIO` objects. The filename extension is derived from `processed_image_mime_type`.

### Decision 3: MIME-to-extension mapping

Use a simple dict mapping `image/png` → `png`, `image/jpeg` → `jpg`, `image/webp` → `webp`, `image/gif` → `gif` with `png` as fallback.

**Rationale**: Matches the supported MIME types in the master-agent API spec. Telegram needs a filename with extension for proper display.

## Risks / Trade-offs

- **[Large processed images]** → Telegram has a 10MB photo limit. Nano Banana Pro outputs are typically well under this. No mitigation needed now; if it becomes an issue, can send as document instead.
- **[Caption truncation]** → Telegram captions are limited to 1024 characters. Truncating may cut off important text. Acceptable trade-off — the full text is still logged.
