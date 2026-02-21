## Context

The Telegram bot already handles text, voice, and image messages using a consistent pattern:
1. Handler downloads/decodes the media from Telegram
2. `BackendClient` base64-encodes and POSTs to master-agent
3. Handler returns the agent's text response to the user

The master-agent already exposes `POST /api/document` which:
- Accepts `conversation_id`, `document_base64`, `mime_type`, `filename`, optional `metadata`
- Uploads the file to GCS
- Calls docling-agent for structured extraction
- Returns a `response` string (AI-generated summary/answer)

The docling-agent accepts `gs://` paths and supports PDF, DOCX, PPTX, XLSX, HTML, Markdown, CSV, and raster image formats.

## Goals / Non-Goals

**Goals:**
- Handle `filters.Document` Telegram messages (any file sent as a document)
- Download the file from Telegram, base64-encode it, forward to master-agent `/api/document`
- Return the agent text response to the user
- Support file caption as an optional user prompt (forwarded in metadata or as a separate field if master-agent supports it)
- Use generous timeouts matching the image handler (120 s per-request, 180 s total) since docling processing can be slow

**Non-Goals:**
- File size enforcement beyond Telegram's own 20 MB bot limit
- Streaming responses
- Changes to master-agent or docling-agent code
- Storing documents in the bot's own storage

## Decisions

### 1. Mirror the image handler pattern exactly

The existing `image.py` handler and `forward_image()` client method provide a well-tested template. The document handler will replicate the same structure: download → encode → forward → reply.

**Alternative considered:** A generic media handler that dispatches to image/document paths. Rejected — it adds indirection without benefit; the handlers are small and independent.

### 2. Detect MIME type from Telegram's `document.mime_type`

Telegram provides `message.document.mime_type` directly. We pass it through to master-agent as-is. If Telegram returns `None` (rare), fall back to `application/octet-stream`.

**Alternative:** Sniff MIME type from bytes. Rejected — adds a dependency (`python-magic` or `filetype`) and Telegram's value is reliable enough.

### 3. Use `document.file_name` as the filename

Telegram exposes `message.document.file_name`. We pass it to master-agent so docling can use the extension as a hint. If `None`, default to `document`.

### 4. Caption as user context

If the user attaches a caption to the document, include it in a `prompt` field on the request (master-agent already supports this on the image endpoint; document endpoint should be consistent). If master-agent's document model does not have a `prompt` field, the caption is ignored gracefully on the bot side with a log warning — no error raised.

### 5. Timeout budget: 120 s per-request, 180 s total

Docling processing of large PDFs can take 30–90 s. We use the same budget as the image handler to avoid spurious timeouts.

## Risks / Trade-offs

- **Large files slow to download from Telegram** → Mitigation: Telegram CDN is fast; 20 MB cap limits worst-case download time to a few seconds on Cloud Run.
- **Docling processing timeout for very large PDFs** → Mitigation: 120 s per-request budget; user gets a "Backend unavailable" message if exceeded. A future improvement could stream progress.
- **Unsupported MIME types** → Master-agent / docling-agent return an error response; the bot forwards the error text to the user.
- **`file_name` is None** → Handled by defaulting to `"document"`.
