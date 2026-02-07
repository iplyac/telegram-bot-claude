## Why

Текущая реализация использует `session_id = tg_{user_id}`, что не различает личные сообщения и групповые чаты. Нужен стабильный `conversation_id`, который:
- Различает DM и группы
- Передаёт metadata о Telegram контексте
- Позволяет master-agent управлять историей разговоров

## What Changes

### Telegram Bot
- Изменить формирование идентификатора:
  - Private chat: `tg_dm_<user_id>`
  - Group/Supergroup: `tg_group_<chat_id>`
- Изменить формат запроса к master-agent:
  - `session_id` → `conversation_id`
  - Добавить `metadata.telegram` с chat_id, user_id, chat_type
- Бот остаётся stateless (без хранения истории)

### Master Agent
- Обновить API `/api/chat` для приёма нового формата
- Поддержать обратную совместимость (старый формат с session_id)

## Capabilities

### New Capabilities
- `conversation-identity`: Правила формирования conversation_id и формат metadata

### Modified Capabilities
<!-- Нет существующих спецификаций для изменения -->

## Impact

- **telegram-bot**: `tgbot/dispatcher.py`, `tgbot/handlers/voice.py`, `tgbot/services/backend_client.py`
- **master-agent**: API endpoint `/api/chat`, `/api/voice`
- **API Contract**: Изменение формата запроса (с обратной совместимостью)
