# Рекомендации по обновлению спецификации v18

На основе проблем, выявленных при деплое v17, предлагаются следующие изменения.

---

## 1. Health Check Endpoints

### Проблема
Endpoint `/healthz` блокируется на уровне Google Cloud Run/CDN и возвращает 404 от Google, а не от приложения. При этом `/healthz/bot` работает корректно.

### Рекомендация
Добавить альтернативный endpoint `/health` как основной:

```python
@app.get("/healthz")
@app.get("/health")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

### Изменение в спецификации
```markdown
FASTAPI ENDPOINTS (MANDATORY):
- GET /health -> HTTP 200, {"status":"ok"} (PRIMARY)
- GET /healthz -> HTTP 200, {"status":"ok"} (ALIAS, may be blocked by Cloud Run)
- GET /healthz/bot -> HTTP 200 JSON with bot status
```

---

## 2. Lifespan и Webhook Setup

### Проблема
В asynccontextmanager lifespan:
- Код **до** `yield` — это startup
- Код **после** `yield` — это **shutdown**, НЕ post-startup

Webhook setup был размещён после `yield`, что означало его выполнение при shutdown, а не после запуска сервера.

### Рекомендация
Webhook setup ДОЛЖЕН выполняться ДО `yield`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    # ... config, создание клиентов ...

    if webhook_url:
        # Webhook setup ЗДЕСЬ, до yield
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.bot.set_webhook(url=full_webhook_url, secret_token=webhook_secret)
    else:
        # Polling mode
        polling_task = asyncio.create_task(start_polling(tg_app))

    yield  # Сервер начинает принимать запросы

    # === SHUTDOWN ===
    # Только cleanup код здесь
```

### Изменение в спецификации
```markdown
LIFESPAN SEQUENCING (MANDATORY):

Startup (before yield):
1-8) ... existing steps ...
9) Determine mode:
   - If webhook mode:
     - await tg_app.initialize()
     - await tg_app.start()
     - await tg_app.bot.set_webhook(url, secret_token)
     - On failure: fallback to polling
   - If polling mode:
     - Start polling as asyncio.Task

yield  # Server starts accepting requests here

Shutdown (after yield):
- ONLY cleanup code (stop polling, close clients, shutdown app)
- NO initialization or setup code after yield
```

---

## 3. Secret Manager: Concatenated Key-Value Format

### Проблема
Секреты в Secret Manager могут храниться в формате без newline между ключами:
```
TELEGRAM_BOT_USERNAME=botnameTELEGRAM_BOT_TOKEN=123456:ABC...
```

Функция `extract_bot_token` с `split("\n")` не обрабатывает такой формат.

### Рекомендация
Использовать regex для извлечения токена:

```python
def extract_bot_token(payload: str) -> Optional[str]:
    import re

    if not payload:
        return None

    # Regex для поиска токена в любом месте строки
    # Формат токена: digits:alphanumeric
    match = re.search(r'TELEGRAM_BOT_TOKEN=(\d+:[A-Za-z0-9_-]+)', payload)
    if match:
        return match.group(1)

    # Fallback для multi-line формата
    for line in payload.strip().split("\n"):
        if line.strip().startswith("TELEGRAM_BOT_TOKEN="):
            return line.strip()[len("TELEGRAM_BOT_TOKEN="):]

    # Single-line format (just the token)
    if "=" not in payload:
        return payload.strip()

    return None
```

### Изменение в спецификации
```markdown
SECRET VALUE EXTRACTION (MANDATORY):

Secret Manager secrets MAY be stored in multiple formats:
1) Single-line: just the token value
2) Multi-line key=value pairs separated by newlines
3) Concatenated key=value pairs WITHOUT newlines (e.g., KEY1=val1KEY2=val2)

Extraction logic MUST handle ALL formats using regex:
- Pattern: TELEGRAM_BOT_TOKEN=(\d+:[A-Za-z0-9_-]+)
- This extracts token even when concatenated with other keys
```

---

## 4. Token Extraction для Environment Variables

### Проблема
Cloud Run монтирует секрет целиком в env var через `--set-secrets`. Если секрет содержит несколько ключей, весь контент попадает в `TELEGRAM_BOT_TOKEN` env var.

Функция `get_bot_token()` возвращала raw env var без применения `extract_bot_token`.

### Рекомендация
Применять `extract_bot_token` к значению из env var:

```python
def get_bot_token() -> str:
    token_env = os.getenv("TELEGRAM_BOT_TOKEN")
    if token_env:
        # Extract token in case env var contains multi-key format
        token = extract_bot_token(token_env)
        if token:
            sanitized = sanitize_value(token)
            if sanitized:
                return sanitized

    # ... Secret Manager fallback ...
```

### Изменение в спецификации
```markdown
TOKEN RESOLUTION ORDER (MANDATORY; in config.get_bot_token):
1) If TELEGRAM_BOT_TOKEN env var is set:
   - Apply extract_bot_token() to handle multi-key formats
   - Apply sanitize_value()
   - Return if valid
2) Else resolve from Secret Manager (existing logic)
3) If still missing → raise ValueError
```

---

## 5. Token Masking в логах

### Проблема
При ошибке установки webhook, токен попал в лог:
```
Failed to set webhook: The token `...actual_token...` was rejected
```

### Рекомендация
Маскировать токены в сообщениях об ошибках:

```python
def mask_token(message: str) -> str:
    """Mask any bot tokens in error messages."""
    import re
    return re.sub(r'\d{8,}:[A-Za-z0-9_-]{20,}', '***TOKEN***', message)

# В обработке ошибок:
except Exception as e:
    error_msg = mask_token(str(e))
    logger.warning(f"Failed to set webhook: {error_msg}")
```

### Изменение в спецификации
```markdown
LOGGING REQUIREMENTS (MANDATORY):
- ... existing rules ...
- Error messages MUST be sanitized to mask any accidentally included tokens
- Token pattern for masking: \d{8,}:[A-Za-z0-9_-]{20,}
- Masked replacement: "***TOKEN***" or "[REDACTED]"
```

---

## 6. Dockerfile Cache Busting

### Проблема
Cloud Build кэширует Docker слои. При изменении только Python файлов без изменения Dockerfile, старый код может остаться в кэше.

### Рекомендация
Добавить ARG для инвалидации кэша:

```dockerfile
FROM --platform=linux/amd64 python:3.11-slim

ARG BUILD_TIMESTAMP
# или использовать в deploy-bot.sh:
# --build-arg BUILD_TIMESTAMP=$(date +%s)
```

Или изменить порядок COPY команд:

```dockerfile
# Сначала код (часто меняется)
COPY secret_manager.py .
COPY app.py .
COPY tgbot/ ./tgbot/

# Потом зависимости (редко меняются) — НЕТ, это неправильно для кэширования

# Лучше: добавить .dockerignore и использовать --no-cache при необходимости
```

### Изменение в спецификации
```markdown
DEPLOYMENT SCRIPTS (MANDATORY):

deploy-bot.sh:
- For forced rebuild without cache, support optional --no-cache flag:
  gcloud builds submit --tag ... --no-cache
```

---

## 7. README: Cloud Run специфика

### Рекомендация
Добавить в README секцию о Cloud Run особенностях:

```markdown
## Cloud Run Specifics

### Reserved Endpoints
- `/healthz` may be intercepted by Cloud Run infrastructure
- Use `/health` as primary health check endpoint

### Secret Mounting
- `--set-secrets` mounts entire secret content to env var
- Ensure secret contains ONLY the token, OR use extraction logic
- Recommended: store token as single value without key prefix
```

---

## Сводка изменений для v18

| #  | Область | Изменение |
|----|---------|-----------|
| 1  | Endpoints | Добавить `/health` как primary, `/healthz` как alias |
| 2  | Lifespan | Webhook setup ДОЛЖЕН быть ДО yield |
| 3  | Secret extraction | Regex для concatenated format |
| 4  | Config | Применять extract_bot_token к env var |
| 5  | Logging | Маскировать токены в ошибках |
| 6  | Deployment | Документировать --no-cache опцию |
| 7  | README | Секция Cloud Run specifics |

---

## Пример обновлённого SELF-CHECKS

```markdown
SELF-CHECKS (MANDATORY):

Cloud Run Compatibility (NEW in v18):
- /health endpoint exists as primary health check
- /healthz is alias (may be blocked by Cloud Run)
- Webhook setup occurs BEFORE yield in lifespan
- extract_bot_token handles concatenated key=value format
- extract_bot_token applied to TELEGRAM_BOT_TOKEN env var
- Token masking in error log messages
```
