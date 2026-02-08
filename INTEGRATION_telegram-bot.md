# Интеграция с Telegram Bot

Этот документ описывает как telegram-bot обращается к master-agent.

## Обзор

```
┌─────────────────┐                     ┌─────────────────┐
│  telegram-bot   │───public HTTPS────▶ │  master-agent   │
│  (Cloud Run)    │                     │  (Cloud Run)    │
└─────────────────┘                     └─────────────────┘
        │                                       │
        │ AGENT_API_URL env var                 │ ingress: all
        └───────────────────────────────────────┘
```

## Текущая конфигурация

| Сервис | Настройка | Значение |
|--------|-----------|----------|
| master-agent | Service name | `master-agent` |
| master-agent | Region | `europe-west4` |
| master-agent | Ingress | `all` (публично доступен) |
| master-agent | URL | `https://master-agent-3qblthn7ba-ez.a.run.app` |
| telegram-bot | AGENT_API_URL | URL master-agent |

## Требования к master-agent

### 1. Имя сервиса

Service name MUST быть `master-agent`.

В `deploy-agent.sh`:
```bash
SERVICE_NAME="${SERVICE_NAME:-master-agent}"
```

### 2. Ingress настройки

Ingress MUST быть `all` для публичного доступа.

В `gcloud run deploy`:
```bash
--ingress=all
```

Или через Console: Cloud Run → master-agent → Security → Ingress → "All"

### 3. API Endpoints

Telegram-bot использует следующие endpoints:

| Endpoint | Method | Назначение |
|----------|--------|------------|
| `/api/chat` | POST | Текстовые сообщения |
| `/api/voice` | POST | Голосовые сообщения |
| `/api/image` | POST | Изображения (описание + обработка через Nano Banana Pro) |

#### POST /api/chat

**Request:**
```json
{
  "session_id": "tg_123456789",
  "message": "Привет!"
}
```

**Response (200):**
```json
{
  "response": "Привет! Как я могу помочь?"
}
```

**Response (400):**
```json
{
  "error": "session_id and message are required"
}
```

**Response (500):**
```json
{
  "error": "Agent unavailable, please try again later"
}
```

#### POST /api/voice

**Request:**
```json
{
  "session_id": "tg_123456789",
  "audio_base64": "<base64-encoded-ogg>",
  "mime_type": "audio/ogg"
}
```

**Response (200):**
```json
{
  "response": "Ответ агента на голосовое сообщение",
  "transcription": "Расшифровка голоса"
}
```

#### POST /api/image

**Request:**
```json
{
  "conversation_id": "tg_dm_234759359",
  "image_base64": "<base64-encoded-image>",
  "mime_type": "image/jpeg",
  "prompt": "Убери фон с этого изображения",
  "metadata": {
    "telegram": {
      "chat_id": 234759359,
      "user_id": 123456,
      "chat_type": "private"
    }
  }
}
```

**Response (200) — без промпта (описание):**
```json
{
  "response": "На изображении кот сидит на подоконнике...",
  "description": "Рыжий полосатый кот на деревянном подоконнике.",
  "processed_image_base64": null,
  "processed_image_mime_type": null
}
```

**Response (200) — с промптом (обработка через Nano Banana Pro):**
```json
{
  "response": "Вот изображение с убранным фоном.",
  "description": "Я убрал фон, оставив только кота.",
  "processed_image_base64": "<base64-обработанное-изображение>",
  "processed_image_mime_type": "image/png"
}
```

**Поведение:**
- **Без `prompt`** — изображение описывается через Gemini, возвращается текст
- **С `prompt`** — изображение обрабатывается через Nano Banana Pro (Gemini 3 Pro Image), возвращается текст + обработанное изображение
- `processed_image_base64` = null если модель не вернула изображение

**Telegram-bot должен:**
1. Передавать `caption` фото как `prompt`
2. Проверять `processed_image_base64` в ответе
3. Если есть — отправлять обработанное изображение как фото с текстом в caption
4. Если нет — отправлять текстовый ответ

## Почему НЕ используется Internal DNS

Cloud Run **НЕ поддерживает** нативный internal DNS (`.run.internal`).

Формат `https://service.region.run.internal` — это конвенция из community-проекта [runsd](https://github.com/ahmetb/runsd), а не официальная функция Google Cloud.

Для настоящего internal networking требуется [Private Service Connect](https://cloud.google.com/run/docs/securing/private-networking), что значительно сложнее.

**Текущее решение:** публичный URL с HTTPS. Это безопасно — Cloud Run обеспечивает TLS.

## Безопасность (TODO)

Сейчас master-agent публично доступен. Варианты защиты:

1. **IAM authentication** — Cloud Run проверяет identity вызывающего сервиса
2. **API Key** — shared secret в headers
3. **Private Service Connect** — полностью приватная сеть

## Деплой

### Telegram-bot

```bash
AGENT_API_URL=https://master-agent-3qblthn7ba-ez.a.run.app ./deploy-bot.sh
```

### Master-agent

```bash
SERVICE_NAME=master-agent ./deploy-agent.sh
```

## Проверка интеграции

```bash
# Health check
curl https://master-agent-3qblthn7ba-ez.a.run.app/health

# Chat endpoint
curl -X POST https://master-agent-3qblthn7ba-ez.a.run.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "ping"}'
```
