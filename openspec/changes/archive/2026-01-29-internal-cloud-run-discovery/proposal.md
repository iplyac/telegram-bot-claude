## Why

Сейчас `AGENT_API_URL` должен быть явно задан через env var. При деплое создаётся циклическая зависимость: нужно знать URL агента до деплоя бота. Cloud Run имеет встроенный Internal DNS — сервисы доступны по детерминированному URL `https://[SERVICE].[REGION].run.internal` внутри VPC.

## What Changes

- Добавить fallback в `get_agent_api_url()`: если env var не задан → использовать Internal DNS URL
- URL формируется как `https://master-agent.{region}.run.internal`
- Никаких новых зависимостей или SDK

```
AGENT_API_URL env var ──┬── set ───────▶ использовать напрямую
                        │
                        └── not set ──▶ Internal DNS
                                              │
                                              ▼
                                 https://master-agent.{region}.run.internal
```

## Capabilities

### New Capabilities
- `agent-url-resolution`: Автоматическое определение URL master-agent через Internal Cloud Run DNS

### Modified Capabilities
<!-- Нет изменений в существующих требованиях -->

## Impact

- `tgbot/config.py` — модифицировать `get_agent_api_url()` с fallback на Internal DNS
- Инфраструктура: telegram-bot нужен VPC Egress, master-agent — internal ingress
