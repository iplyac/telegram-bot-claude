## 1. Create GetPromptCommand class

- [x] 1.1 Create `tgbot/commands/getprompt.py` with `GetPromptCommand` class
- [x] 1.2 Implement `name` property returning `"getprompt"`
- [x] 1.3 Implement `description` property
- [x] 1.4 Add `__init__` accepting `agent_api_url: Optional[str]`

## 2. Implement handle method

- [x] 2.1 Check if `agent_api_url` is configured
- [x] 2.2 Make GET request to `/api/prompt` using `httpx`
- [x] 2.3 Parse response and extract `prompt` and `length`
- [x] 2.4 Truncate prompt to 4000 chars if needed
- [x] 2.5 Format response with code block and length info
- [x] 2.6 Handle HTTP errors with user-friendly message

## 3. Register command in dispatcher

- [x] 3.1 Import `GetPromptCommand` in `tgbot/dispatcher.py`
- [x] 3.2 Create `GetPromptCommand` instance with `agent_api_url`
- [x] 3.3 Register command handler

## 4. Testing

- [x] 4.1 Add unit tests in `tests/test_getprompt_command.py`
- [x] 4.2 Test success scenario with short prompt
- [x] 4.3 Test success scenario with long prompt (truncation)
- [x] 4.4 Test API error scenario
- [x] 4.5 Test backend not configured scenario
