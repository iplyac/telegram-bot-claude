## 1. Create SessionInfoCommand class

- [x] 1.1 Create `tgbot/commands/sessioninfo.py` with `SessionInfoCommand` class extending `BaseCommand`
- [x] 1.2 Implement `name` property returning `"sessioninfo"`
- [x] 1.3 Implement `description` property returning command help text
- [x] 1.4 Add `__init__` accepting `agent_api_url: Optional[str]` parameter

## 2. Implement handle method

- [x] 2.1 Derive `conversation_id` from chat type (`tg_dm_{chat_id}` or `tg_group_{chat_id}`)
- [x] 2.2 Check if `agent_api_url` is configured, reply with error if not
- [x] 2.3 Make POST request to `/api/session-info` endpoint using `httpx`
- [x] 2.4 Parse response and format reply message for active session
- [x] 2.5 Format reply message for non-existent session
- [x] 2.6 Handle HTTP errors with user-friendly messages

## 3. Register command in dispatcher

- [x] 3.1 Import `SessionInfoCommand` in `tgbot/dispatcher.py`
- [x] 3.2 Create `SessionInfoCommand` instance with `agent_api_url` from config
- [x] 3.3 Register command handler via `application.add_handler(CommandHandler(...))`

## 4. Testing

- [x] 4.1 Add unit tests for `SessionInfoCommand` in `tests/test_sessioninfo_command.py`
- [x] 4.2 Test conversation_id derivation for private and group chats
- [x] 4.3 Test error handling scenarios (backend not configured, HTTP error, invalid response)
