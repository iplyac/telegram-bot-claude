## Why

The Telegram bot currently supports text, voice, and image messages, but users cannot send documents (PDFs, DOCX, PPTX, XLSX, etc.) for AI processing. Adding document support closes this gap and enables the full document-intelligence pipeline: Telegram → master-agent (GCS upload) → docling-agent (structured extraction) → AI response.

## What Changes

- New `document` handler in the Telegram bot that intercepts `filters.Document` messages
- New `forward_document()` method in `BackendClient` that POSTs base64-encoded documents to master-agent `/api/document`
- Handler registration in `dispatcher.py` for `filters.Document`
- Master-agent `/api/document` endpoint is already implemented; no changes needed there
- Supported formats: PDF, DOCX, PPTX, XLSX, HTML, Markdown, CSV, and image-as-document types (PNG, JPEG, TIFF, BMP, WEBP)

## Capabilities

### New Capabilities
- `document-handler`: Receives Telegram document messages, downloads the file, base64-encodes it, and forwards it to master-agent `/api/document` with filename, MIME type, and conversation metadata. Returns the agent text response to the user.

### Modified Capabilities

_(none — existing message-flow-logging and agent-url-resolution specs are not changing their requirements)_

## Impact

- **Files added:** `tgbot/handlers/document.py`
- **Files modified:** `tgbot/services/backend_client.py` (new `forward_document` method), `tgbot/dispatcher.py` (register document handler)
- **External APIs:** master-agent `POST /api/document` (already exists) — accepts `conversation_id`, `document_base64`, `mime_type`, `filename`, optional `metadata`; returns `response` string
- **Dependencies:** no new Python packages required (uses existing `httpx`, `python-telegram-bot`)
- **Timeout:** document processing via docling may take 30–120 s; timeout budget must match image handler (120 s per request, 180 s total)
