## Context

Текущее логирование:
- Использует стандартный `logging` модуль
- Логи в текстовом формате (не JSON)
- Нет correlation ID для связывания логов одного message flow
- Нет единой точки настройки логирования

Message flow сейчас:
```
Telegram webhook → dispatcher._handle_text_message → backend_client.forward_message → agent
                                                                                     ↓
Telegram ← update.message.reply_text ← response ←──────────────────────────────────────
```

## Goals / Non-Goals

**Goals:**
- Structured JSON logging для Cloud Logging
- Correlation ID (`request_id`) для связи логов одного запроса
- Логирование всех этапов: receive → forward → response → reply
- Латентность каждого этапа

**Non-Goals:**
- Metrics/tracing (OpenTelemetry) — отдельный change
- Log aggregation/alerting — настраивается в GCP
- Message content logging (privacy)

## Decisions

### 1. JSON Log Formatter

**Решение:** Использовать `python-json-logger` для JSON форматирования.

**Обоснование:**
- Cloud Logging автоматически парсит JSON
- Поддержка structured fields (extra)
- Минимальные изменения в коде

### 2. Correlation ID

**Решение:** Генерировать `request_id` (UUID4) при получении webhook и передавать через весь flow.

**Формат:** `req_{uuid4_short}` (например: `req_a1b2c3d4`)

**Передача:** Через параметр функций (не contextvars, для простоты).

### 3. Log Points

| Stage | Log Level | Fields |
|-------|-----------|--------|
| Webhook received | INFO | request_id, update_id, user_id, message_type |
| Agent request start | INFO | request_id, session_id, endpoint |
| Agent response | INFO | request_id, status_code, latency_ms |
| Reply sent | INFO | request_id, latency_total_ms |
| Error | ERROR | request_id, error_type, error_message |

### 4. Logging Setup

**Решение:** Единая функция `setup_logging()` в `tgbot/logging_config.py`.

Конфигурация:
- Root logger → JSON formatter
- Level из `LOG_LEVEL` env var (default: INFO)
- Подавление verbose логов от `httpx`, `telegram`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Performance overhead от JSON serialization | Минимален, ~1ms per log |
| request_id не попадает во все логи | Передавать явно, не использовать глобальное состояние |
| Verbose логи от библиотек | Настроить log levels для httpx, telegram |
