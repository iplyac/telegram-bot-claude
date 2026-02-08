## 1. Image Handler — Processed Image Reply

- [x] 1.1 Add `import io` and `from telegram import InputFile` to `tgbot/handlers/image.py`
- [x] 1.2 Add MIME-to-extension mapping dict (`MIME_TO_EXT`) in `image.py`
- [x] 1.3 After receiving `result` from `backend_client.forward_image()`, check `processed_image_base64` and `processed_image_mime_type`
- [x] 1.4 If processed image present: decode base64, wrap in `BytesIO`, send via `reply_photo(photo=InputFile(...), caption=text[:1024])`
- [x] 1.5 If no processed image: keep existing `reply_text(response_text)` behavior

## 2. Tests

- [x] 2.1 Add test: photo handler replies with photo when `processed_image_base64` is present in response
- [x] 2.2 Add test: photo handler replies with text when `processed_image_base64` is null
- [x] 2.3 Add test: caption is truncated to 1024 characters when text response is long
- [x] 2.4 Run full test suite to verify no regressions
