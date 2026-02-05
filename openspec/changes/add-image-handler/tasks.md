## 1. Add forward_image to BackendClient

- [x] 1.1 Add `forward_image` method to `tgbot/services/backend_client.py`
- [x] 1.2 Method accepts: conversation_id, image_base64, mime_type, prompt, metadata, request_id
- [x] 1.3 POST to `/api/image` with JSON payload matching API spec
- [x] 1.4 Use existing `_post_with_retry` for retry logic

## 2. Create image handler module

- [x] 2.1 Create `tgbot/handlers/image.py` following voice handler pattern
- [x] 2.2 Import `_derive_conversation_id` helper (or duplicate from voice.py)
- [x] 2.3 Implement `handle_photo_message` function

## 3. Implement handle_photo_message

- [x] 3.1 Get largest photo size from `update.message.photo[-1]`
- [x] 3.2 Download photo using `context.bot.get_file(file_id)`
- [x] 3.3 Base64-encode downloaded bytes
- [x] 3.4 Get MIME type (default to "image/jpeg" if not available)
- [x] 3.5 Use caption as prompt or default "What is in this image?"
- [x] 3.6 Call `backend_client.forward_image`
- [x] 3.7 Reply with response text

## 4. Register handler in dispatcher

- [x] 4.1 Import `handle_photo_message` in `tgbot/dispatcher.py`
- [x] 4.2 Create wrapper function with backend_client closure
- [x] 4.3 Register with `MessageHandler(filters.PHOTO, ...)`

## 5. Error handling

- [x] 5.1 Handle backend not configured (AGENT_API_URL is None)
- [x] 5.2 Handle HTTP errors with user-friendly message
- [x] 5.3 Handle download failures
- [x] 5.4 Add logging for all error cases

## 6. Testing

- [x] 6.1 Add unit tests in `tests/test_image_handler.py`
- [x] 6.2 Test photo with caption
- [x] 6.3 Test photo without caption (default prompt)
- [x] 6.4 Test error scenarios
