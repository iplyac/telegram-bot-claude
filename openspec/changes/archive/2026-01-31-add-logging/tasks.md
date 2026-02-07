## 1. Setup logging infrastructure

- [x] 1.1 Add `python-json-logger` to requirements.txt
- [x] 1.2 Create `tgbot/logging_config.py` with `setup_logging()` function
- [x] 1.3 Configure JSON formatter for root logger
- [x] 1.4 Set log levels for httpx, telegram libraries to WARNING

## 2. Add correlation ID support

- [x] 2.1 Create `generate_request_id()` function (format: `req_{8-char-hex}`)
- [x] 2.2 Generate request_id in webhook handler (telegram_bot.py)
- [x] 2.3 Pass request_id through handler functions

## 3. Update dispatcher logging

- [x] 3.1 Add request_id to text message handler logs
- [x] 3.2 Add request_id to voice message handler logs
- [x] 3.3 Log message receive with message_type field
- [x] 3.4 Log reply sent with latency_total_ms

## 4. Update backend_client logging

- [x] 4.1 Add request_id parameter to forward_message/forward_voice
- [x] 4.2 Log agent request start with endpoint
- [x] 4.3 Log agent response with latency_ms
- [x] 4.4 Log errors with full context

## 5. Initialize logging in application

- [x] 5.1 Call setup_logging() in telegram_bot.py before app start
- [x] 5.2 Test JSON log output locally
- [x] 5.3 Verify logs in Cloud Logging after deploy
