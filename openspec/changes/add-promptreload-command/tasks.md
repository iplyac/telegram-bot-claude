## 1. Create PromptReloadCommand class

- [x] 1.1 Create `tgbot/commands/promptreload.py` with `PromptReloadCommand` class
- [x] 1.2 Implement `name` property returning `"promptreload"`
- [x] 1.3 Implement `description` property
- [x] 1.4 Add `__init__` accepting `agent_api_url: Optional[str]`

## 2. Implement handle method

- [x] 2.1 Check if `agent_api_url` is configured
- [x] 2.2 Make POST request to `/api/reload-prompt` using `httpx`
- [x] 2.3 Parse response and handle success case
- [x] 2.4 Handle error status from API response
- [x] 2.5 Handle HTTP errors with user-friendly message

## 3. Register command in dispatcher

- [x] 3.1 Import `PromptReloadCommand` in `tgbot/dispatcher.py`
- [x] 3.2 Create `PromptReloadCommand` instance with `agent_api_url`
- [x] 3.3 Register command handler

## 4. Testing

- [x] 4.1 Add unit tests in `tests/test_promptreload_command.py`
- [x] 4.2 Test success scenario
- [x] 4.3 Test API error scenario
- [x] 4.4 Test backend not configured scenario
