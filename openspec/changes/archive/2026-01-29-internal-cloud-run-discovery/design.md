## Context

Telegram-bot и master-agent работают как Cloud Run сервисы в GCP. Cloud Run предоставляет Internal DNS для сервисов внутри VPC — каждый сервис доступен по стабильному URL без необходимости знать хеш ревизии.

```
┌─────────────────┐                  ┌──────────────────────┐
│  telegram-bot   │───VPC Egress───▶ │  Internal DNS        │
│  (Cloud Run)    │                  │                      │
└─────────────────┘                  │  master-agent.       │
                                     │  europe-west4.       │
                                     │  run.internal        │
                                     └──────────┬───────────┘
                                                │
                                                ▼
                                     ┌──────────────────────┐
                                     │  master-agent        │
                                     │  (Cloud Run)         │
                                     │  ingress: internal   │
                                     └──────────────────────┘
```

## Goals / Non-Goals

**Goals:**
- Автоматическое обнаружение master-agent без ручной настройки URL
- Сохранить обратную совместимость: env var `AGENT_API_URL` имеет приоритет
- Zero runtime dependencies — только конкатенация строк

**Non-Goals:**
- Service Directory или другие registry
- Кэширование или health checks
- Поддержка multi-region или multi-project

## Decisions

### 1. Порядок резолюции AGENT_API_URL

```
1. AGENT_API_URL env var (если задан)
      │
      ▼ (не задан)
2. Internal DNS URL
      │
      ▼
   https://master-agent.{region}.run.internal
```

**Rationale:** Env var для локальной разработки и тестов. Internal DNS для production.

### 2. Формат Internal DNS URL

```
https://master-agent.{region}.run.internal
```

| Компонент | Значение | Источник |
|-----------|----------|----------|
| protocol | `https` | всегда |
| service | `master-agent` | hardcoded |
| region | `get_region()` | существующая функция |
| domain | `run.internal` | GCP Internal DNS |

**Rationale:** Детерминированный URL — не зависит от хеша ревизии. Имя сервиса `master-agent` фиксировано как часть архитектуры.

### 3. Никаких новых зависимостей

Вся логика — простая конкатенация строк в `config.py`:

```python
def get_agent_api_url() -> Optional[str]:
    url = sanitize_value(os.getenv("AGENT_API_URL"))
    if url:
        return url

    region = get_region()
    return f"https://master-agent.{region}.run.internal"
```

**Rationale:**
- Zero cold start penalty
- Нет SDK, нет IAM
- Нет точек отказа кроме самой сети

### 4. Инфраструктурные требования

| Сервис | Настройка | Значение |
|--------|-----------|----------|
| telegram-bot | VPC Egress | Direct VPC или VPC Connector |
| master-agent | Ingress | "internal" или "all" |

**Rationale:** Internal DNS работает только внутри VPC. Без VPC Egress бот не сможет резолвить `.run.internal` домены.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| VPC не настроен | Документировать требования; бот получит connection error |
| master-agent недоступен | Стандартная обработка ошибок HTTP |
| Неправильный region | Использовать тот же region что у бота |
