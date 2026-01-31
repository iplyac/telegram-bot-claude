## Why

Сейчас деплой telegram-bot выполняется вручную через `deploy-bot.sh`. Нужна автоматизация: push в main → автоматический деплой в Cloud Run.

## What Changes

- Добавить `cloudbuild.yaml` для автоматической сборки и деплоя
- Настроить Cloud Build trigger на push в main branch
- Перенести логику из `deploy-bot.sh` в `cloudbuild.yaml`
- Сохранить `deploy-bot.sh` для ручного деплоя (fallback)

## Capabilities

### New Capabilities
- `cicd-pipeline`: Автоматический CI/CD пайплайн через Cloud Build trigger

### Modified Capabilities
<!-- Нет изменений в существующих спецификациях -->

## Impact

- **Новые файлы**: `cloudbuild.yaml`
- **Cloud Build**: Настройка trigger в GCP Console или через gcloud
- **IAM**: Cloud Build service account нужны права на Cloud Run deploy и Secret Manager
- **Webhook**: Автоматическая настройка webhook после деплоя (как в deploy-bot.sh)
