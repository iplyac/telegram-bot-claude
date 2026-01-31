## Context

Telegram-bot деплоится вручную через `deploy-bot.sh`. Скрипт выполняет:
1. `gcloud builds submit` — сборка Docker image
2. `gcloud run deploy` — деплой в Cloud Run
3. `curl setWebhook` — настройка Telegram webhook

Нужен автоматический деплой при push в main branch.

## Goals / Non-Goals

**Goals:**
- Автоматический деплой при push в main
- Сохранить всю функциональность deploy-bot.sh (build, deploy, webhook setup)
- Минимальная конфигурация

**Non-Goals:**
- Multiple environments (dev/staging/prod) — только prod
- Approval workflows — не нужны
- Cloud Deploy — overkill для текущих задач
- Тесты в пайплайне — добавим позже

## Decisions

### 1. Cloud Build trigger на push в main

**Решение:** Cloud Build trigger с фильтром на `main` branch.

**Альтернативы:**
- GitHub Actions → требует отдельных credentials для GCP
- Cloud Deploy → overkill, нет multiple environments

**Обоснование:** Cloud Build нативно интегрирован с GCP, уже используется в deploy-bot.sh.

### 2. Структура cloudbuild.yaml

**Решение:** 4 шага:
1. Build image (`docker build`)
2. Push image (`docker push`)
3. Deploy to Cloud Run (`gcloud run deploy`)
4. Setup webhook (`curl setWebhook`)

**Обоснование:** Повторяет логику deploy-bot.sh.

### 3. Secrets через Secret Manager

**Решение:**
- `TELEGRAM_BOT_TOKEN` — уже в Secret Manager, подключается к Cloud Run как secret
- Webhook secret — деривируется из bot token в runtime (sha256)

**Альтернативы:**
- Передать webhook secret как отдельный secret → лишняя сложность

### 4. Service Account permissions

**Решение:** Cloud Build service account нужны роли:
- `roles/run.admin` — деплой в Cloud Run
- `roles/secretmanager.secretAccessor` — чтение TELEGRAM_BOT_TOKEN
- `roles/iam.serviceAccountUser` — impersonate Cloud Run service account

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Webhook setup fails → bot не получает сообщения | Retry в cloudbuild.yaml, fallback на ручной deploy-bot.sh |
| Secrets exposure в логах | Не логировать token, использовать `--quiet` флаги |
| Broken main → авто-деплой сломанного кода | Добавить тесты в пайплайн (будущее улучшение) |

## Migration Plan

1. Создать `cloudbuild.yaml`
2. Настроить IAM permissions для Cloud Build service account
3. Создать trigger в GCP Console: GitHub repo → main branch → cloudbuild.yaml
4. Протестировать push в main
5. Сохранить `deploy-bot.sh` как fallback
