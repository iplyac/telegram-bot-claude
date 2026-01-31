## 1. Config Changes

- [x] 1.1 Modify `get_agent_api_url()` in `tgbot/config.py` to return Internal DNS URL when env var not set

## 2. Testing

- [x] 2.1 Add unit test: env var set → returns env var value
- [x] 2.2 Add unit test: env var not set → returns Internal DNS URL
- [x] 2.3 Add unit test: env var empty/whitespace → returns Internal DNS URL

## 3. Documentation

- [x] 3.1 Document VPC Egress requirement for telegram-bot in deploy scripts
