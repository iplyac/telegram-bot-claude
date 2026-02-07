## Why

Сейчас нет visibility в message flow: сложно отслеживать путь сообщения от Telegram через бота к агенту и обратно. Нужен structured logging для отладки и мониторинга в Cloud Logging.

## What Changes

- Добавить structured logging (JSON) для всех этапов обработки сообщения
- Логировать: incoming message → agent request → agent response → reply sent
- Использовать correlation ID для связи логов одного message flow
- Интеграция с Google Cloud Logging

## Capabilities

### New Capabilities
- `message-flow-logging`: Structured logging для отслеживания пути сообщения через систему

### Modified Capabilities
<!-- Нет изменений в существующих спецификациях -->

## Impact

- **Код**: `tgbot/handlers/`, `tgbot/services/backend_client.py`, `tgbot/dispatcher.py`
- **Зависимости**: `python-json-logger` или встроенный JSON formatter
- **Cloud Logging**: Логи будут доступны в GCP Console с фильтрацией по correlation ID
