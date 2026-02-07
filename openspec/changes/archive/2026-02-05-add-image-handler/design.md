## Context

The telegram-bot already has a voice handler (`tgbot/handlers/voice.py`) that follows a pattern:
1. Receive message from Telegram
2. Download media file
3. Base64-encode
4. Forward to master-agent API
5. Reply with response

Master-agent now exposes `POST /api/image` endpoint with similar structure to `/api/voice`. We need to add an image handler following the same pattern.

## Goals / Non-Goals

**Goals:**
- Handle photo messages from Telegram (single photos, not albums)
- Download image, encode to base64, forward to `/api/image`
- Use photo caption as prompt (or default prompt if no caption)
- Add `forward_image` method to `BackendClient`
- Support common image formats (JPEG, PNG, WebP)

**Non-Goals:**
- Album/multiple photo support (future enhancement)
- Document images (PDF, etc.) - only photos
- Image compression or resizing (Telegram handles this)
- Inline image responses

## Decisions

### 1. Handler structure

**Decision:** Create `tgbot/handlers/image.py` following voice handler pattern

**Rationale:** Consistent codebase structure, proven pattern, easy to maintain.

### 2. Which photo size to use

**Decision:** Use largest available photo size (`photo[-1]`)

**Rationale:** Telegram provides multiple sizes. Largest gives best quality for AI analysis. Master-agent can handle large images.

### 3. Default prompt when no caption

**Decision:** Use "What is in this image?" as default prompt

**Rationale:** Provides meaningful response even without user caption. Matches common use case.

### 4. BackendClient integration

**Decision:** Add `forward_image` method to `BackendClient` using existing retry logic

**Rationale:** Consistent with `forward_voice`, reuses retry mechanism, keeps API calls centralized.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large images slow down response | Telegram compresses images; master-agent should handle |
| Missing caption unclear intent | Default prompt provides reasonable fallback |
| Unsupported format | Log warning, return user-friendly error |
