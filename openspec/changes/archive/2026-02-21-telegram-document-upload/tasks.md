## 1. BackendClient: add forward_document method

- [x] 1.1 Add `forward_document(conversation_id, document_base64, mime_type, filename, prompt, metadata, request_id)` method to `tgbot/services/backend_client.py` — POST to `/api/document` with timeout 120 s / max_total_time 180 s
- [x] 1.2 Include `prompt` field in payload only when non-empty (optional field)
- [x] 1.3 Include `metadata` field in payload when provided (same pattern as `forward_image`)

## 2. Document handler

- [x] 2.1 Create `tgbot/handlers/document.py` with `handle_document_message(update, context, backend_client)` function
- [x] 2.2 Extract `message.document` object; guard against missing update fields (user, message, document)
- [x] 2.3 Log incoming document message (request_id, conversation_id, mime_type, file_size, filename)
- [x] 2.4 Guard: if `backend_client.agent_api_url is None`, reply with `MSG_AGENT_NOT_CONFIGURED` and return
- [x] 2.5 Download document bytes via `context.bot.get_file(document.file_id)` + `download_as_bytearray()`
- [x] 2.6 Base64-encode the bytes
- [x] 2.7 Derive MIME type from `document.mime_type` — fallback to `"application/octet-stream"` if None/empty
- [x] 2.8 Derive filename from `document.file_name` — fallback to `"document"` if None
- [x] 2.9 Send `ChatAction.TYPING` before calling backend
- [x] 2.10 Call `backend_client.forward_document(...)` with caption as `prompt` (omit if no caption)
- [x] 2.11 Reply to user with the `response` field from the returned dict; fallback to "Could not process document." if empty
- [x] 2.12 Handle `ValueError` (AGENT_API_URL not configured) and generic `Exception` with appropriate log + user reply
- [x] 2.13 Log reply sent with total latency

## 3. Dispatcher: register document handler

- [x] 3.1 Import `handle_document_message` from `tgbot.handlers.document` in `tgbot/dispatcher.py`
- [x] 3.2 Add document handler closure (same pattern as `_photo_handler`)
- [x] 3.3 Register handler with `MessageHandler(filters.Document.ALL, _document_handler)` — place after photo handler, before unknown command handler

## 4. Tests

- [x] 4.1 Add unit tests for `forward_document` in `tests/` — verify correct URL, payload fields, timeout parameters
- [x] 4.2 Add unit tests for `handle_document_message` — mock `BackendClient.forward_document`, verify happy path reply
- [x] 4.3 Test MIME type fallback (None → `"application/octet-stream"`)
- [x] 4.4 Test filename fallback (None → `"document"`)
- [x] 4.5 Test `AGENT_API_URL` not configured path
- [x] 4.6 Test backend error path (exception → user error reply)
