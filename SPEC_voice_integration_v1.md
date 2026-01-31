# SPEC VERSION: voice-integration-v1
# STATUS: Draft
# TYPE: Supplement
# SUPPLEMENTS: SPEC_tgbot_claudecode_v18.md, SPEC_ai-agent_v1.md
# TARGET PLATFORM: Google Cloud Run
# LAST UPDATED: 2026-01-28

---

## PURPOSE

Дополнение к двум базовым спецификациям (Telegram Bot v18 + AI Agent v1).
Описывает изменения, необходимые для поддержки:
1. Пересылки **текстовых** сообщений из Telegram Bot в AI Agent
2. Пересылки **голосовых** сообщений из Telegram Bot в AI Agent
3. Транскрипции голосовых сообщений + генерации ответа на стороне AI Agent (Gemini multimodal, один вызов)

Данный документ НЕ заменяет базовые спецификации. Все правила, паттерны и требования
базовых спеков остаются в силе. Этот документ описывает ТОЛЬКО дельту изменений.

---

## NON-GOALS

- Отправка голосовых ответов (Text-to-Speech) — не входит в scope
- Обработка видеосообщений — не входит в scope
- Обработка фото/документов — не входит в scope
- Стриминг аудио (WebSocket) — не входит в scope
- Хранение истории голосовых сообщений — не входит в scope

---

## ARCHITECTURE OVERVIEW

```
┌──────────┐    voice OGG     ┌───────────────┐   base64 JSON    ┌──────────────┐    multimodal    ┌────────┐
│ Telegram │ ──────────────► │  Telegram Bot  │ ──────────────► │   AI Agent   │ ──────────────► │ Gemini │
│   User   │                 │  (Cloud Run)   │                 │  (Cloud Run) │                 │  API   │
│          │ ◄────────────── │                │ ◄────────────── │              │ ◄────────────── │        │
└──────────┘   text reply    └───────────────┘  JSON response   └──────────────┘   text response └────────┘
```

### Text Message Flow (existing, needs AGENT_API_URL)
```
User → [text] → Bot → POST /api/chat {session_id, message} → Agent → Gemini → {response}
```

### Voice Message Flow (NEW)
```
User → [voice OGG] → Bot downloads file → base64 encode → POST /api/voice {session_id, audio_base64, mime_type}
     → Agent → Gemini multimodal (audio + prompt) → {response, transcription}
     → Bot sends response to user
```

---

## AI AGENT — CHANGES (MANDATORY)

All changes below apply to the AI Agent service (SPEC_ai-agent_v1.md).

---

### NEW ENDPOINT: POST /api/voice (MANDATORY)

File: `app.py`

#### API CONTRACT

Request JSON MUST be:
```json
{
  "session_id": "tg_<telegram_user_id>",
  "audio_base64": "<base64-encoded-audio-bytes>",
  "mime_type": "audio/ogg"
}
```

Response JSON MUST be:
```json
{
  "response": "<agent_reply_text>",
  "transcription": "<transcribed_text>"
}
```

Rules:
- MUST return HTTP 200 on success
- MUST return Content-Type: application/json
- MUST complete within 30 seconds (matching bot timeout)
- MUST be safe to retry (stateless)
- On error: return HTTP 500 with `{"error": "Agent unavailable, please try again later"}`
- On invalid request (missing fields, empty audio): return HTTP 400 with `{"error": "<description>"}`
- `audio_base64` MUST be standard base64 encoding (RFC 4648)
- `mime_type` MUST be provided by caller; agent MUST pass it through to Gemini as-is
- Supported mime_types: `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`
- MUST NOT log audio content (OK: session_id, audio size in bytes, mime_type, duration)

#### ENDPOINT IMPLEMENTATION (MANDATORY)

```python
@app.post("/api/voice")
async def voice(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    session_id = body.get("session_id", "")
    audio_base64 = body.get("audio_base64", "")
    mime_type = body.get("mime_type", "audio/ogg")

    if not session_id or not audio_base64:
        return JSONResponse(
            status_code=400,
            content={"error": "session_id and audio_base64 are required"},
        )

    try:
        processor: MessageProcessor = request.app.state.processor
        result = await processor.process_voice(session_id, audio_base64, mime_type)
        return result
    except Exception as e:
        error_msg = mask_token(str(e))
        logger.error("Voice error: session_id=%s, error=%s", session_id, error_msg)
        return JSONResponse(
            status_code=500,
            content={"error": "Agent unavailable, please try again later"},
        )
```

---

### LLM CLIENT — NEW METHOD (MANDATORY)

File: `agent/llm_client.py`

Add method to class `LLMClient`:

```python
async def generate_response_from_audio(
    self, audio_base64: str, mime_type: str, session_id: str
) -> dict:
    """
    Send audio to Gemini multimodal API for transcription + response.
    Returns dict with keys: "response", "transcription".
    """
    if self.api_key is None:
        return {
            "response": "AI model not configured. Please contact administrator.",
            "transcription": "",
        }

    url = f"{self.endpoint}/{self.model_name}:generateContent"
    params = {"key": self.api_key}
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_base64,
                        }
                    },
                    {
                        "text": (
                            "You received a voice message. "
                            "First, transcribe the audio exactly as spoken. "
                            "Then, respond to the content naturally.\n\n"
                            "Format your reply EXACTLY as:\n"
                            "[TRANSCRIPTION]\n<exact transcription>\n"
                            "[RESPONSE]\n<your response>"
                        ),
                    },
                ]
            }
        ],
    }

    audio_size = len(audio_base64) * 3 // 4  # approximate decoded size
    logger.info(
        "LLM voice request: session_id=%s, audio_size=%d, mime_type=%s, model=%s",
        session_id,
        audio_size,
        mime_type,
        self.model_name,
    )

    try:
        response = await self.client.post(
            url,
            params=params,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = self._parse_voice_response(raw_text)

        logger.info(
            "LLM voice response: session_id=%s, transcription_length=%d, response_length=%d",
            session_id,
            len(result["transcription"]),
            len(result["response"]),
        )
        return result

    except httpx.TimeoutException as e:
        error_msg = mask_token(str(e))
        logger.error("LLM voice timeout: session_id=%s, error=%s", session_id, error_msg)
        raise RuntimeError(f"LLM request timed out: {error_msg}") from e
    except httpx.HTTPStatusError as e:
        error_msg = mask_token(str(e))
        logger.error(
            "LLM voice HTTP error: session_id=%s, status=%d, error=%s",
            session_id,
            e.response.status_code,
            error_msg,
        )
        raise RuntimeError(f"LLM API error: {error_msg}") from e
    except Exception as e:
        error_msg = mask_token(str(e))
        logger.error("LLM voice error: session_id=%s, error=%s", session_id, error_msg)
        raise RuntimeError(f"LLM error: {error_msg}") from e
```

#### RESPONSE PARSING (MANDATORY)

Add private method to class `LLMClient`:

```python
@staticmethod
def _parse_voice_response(raw_text: str) -> dict:
    """
    Parse Gemini response containing [TRANSCRIPTION] and [RESPONSE] markers.
    Falls back to using full text as response if markers not found.
    """
    transcription = ""
    response = ""

    if "[TRANSCRIPTION]" in raw_text and "[RESPONSE]" in raw_text:
        parts = raw_text.split("[RESPONSE]", 1)
        transcription_part = parts[0]
        response = parts[1].strip() if len(parts) > 1 else ""

        transcription = transcription_part.replace("[TRANSCRIPTION]", "").strip()
    else:
        # Fallback: entire text is the response
        response = raw_text.strip()

    return {
        "response": response,
        "transcription": transcription,
    }
```

Rules:
- If Gemini returns markers `[TRANSCRIPTION]` and `[RESPONSE]` — parse them
- If markers absent — entire text becomes `response`, `transcription` is empty string
- MUST NOT raise on unexpected format; graceful fallback

---

### MESSAGE PROCESSOR — NEW METHOD (MANDATORY)

File: `agent/processor.py`

Add method to class `MessageProcessor`:

```python
async def process_voice(self, session_id: str, audio_base64: str, mime_type: str) -> dict:
    """Process a voice message and return transcription + response."""
    if not audio_base64 or not audio_base64.strip():
        return {
            "response": "Empty audio received. Please send a voice message.",
            "transcription": "",
        }

    try:
        return await self.llm_client.generate_response_from_audio(
            audio_base64, mime_type, session_id
        )
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("Voice processing error: session_id=%s, error=%s", session_id, e)
        raise RuntimeError("Failed to process voice message") from e
```

---

### AGENT — FILES TO MODIFY (MANDATORY)

| File | Change |
|------|--------|
| `app.py` | Add `POST /api/voice` endpoint |
| `agent/llm_client.py` | Add `generate_response_from_audio()` + `_parse_voice_response()` |
| `agent/processor.py` | Add `process_voice()` |

No new files required on agent side.

---

### AGENT — NEW TESTS (MANDATORY)

File: `tests/test_voice_api.py`

```python
# Required test cases:

# test_voice_endpoint_valid_contract
#   POST /api/voice with valid audio_base64 → 200, {"response": ..., "transcription": ...}

# test_voice_endpoint_missing_api_key
#   API key None → 200, response contains "not configured"

# test_voice_endpoint_missing_audio
#   Missing audio_base64 → 400

# test_voice_endpoint_invalid_json
#   Malformed request → 400

# test_voice_endpoint_timeout
#   Mock timeout → 500
```

File: `tests/test_llm_client.py` (extend existing)

```python
# Required additional test cases:

# test_llm_client_voice_no_api_key
#   Returns {"response": "not configured...", "transcription": ""}

# test_llm_client_voice_success
#   Mock Gemini response with [TRANSCRIPTION] and [RESPONSE] markers → parsed correctly

# test_llm_client_voice_fallback_parse
#   Mock Gemini response WITHOUT markers → entire text becomes response, transcription=""

# test_llm_client_voice_api_error
#   Mock API error → raises RuntimeError with masked message
```

---

## TELEGRAM BOT — CHANGES (MANDATORY)

All changes below apply to the Telegram Bot service (SPEC_tgbot_claudecode_v18.md).

---

### BACKEND CLIENT — NEW METHOD (MANDATORY)

File: `tgbot/services/backend_client.py`

Add method to class `BackendClient`:

```python
async def forward_voice(
    self, session_id: str, audio_base64: str, mime_type: str = "audio/ogg"
) -> dict:
    """
    Forward voice message to agent.
    Returns dict with keys: "response", "transcription".
    """
    if self.agent_api_url is None:
        raise ValueError("AGENT_API_URL is not configured")

    url = f"{self.agent_api_url.rstrip('/')}/api/voice"
    payload = {
        "session_id": session_id,
        "audio_base64": audio_base64,
        "mime_type": mime_type,
    }

    # Retry logic: same as forward_message (3 attempts, exponential backoff)
    # Retry on: ConnectError, ConnectTimeout, ReadTimeout, 502/503/504
    # Total wall-clock <= 30s

    response = await self.client.post(url, json=payload)
    response.raise_for_status()

    data = response.json()
    if "response" not in data:
        raise ValueError("Invalid response from agent: missing 'response' field")

    return data
```

Rules:
- MUST follow the same retry policy as `forward_message` (SPEC v18)
- MUST NOT log audio content (OK: session_id, audio size, mime_type)
- MUST NOT swallow exceptions; raise after retries exhausted
- Returns full dict (with both `response` and `transcription` keys)

---

### VOICE MESSAGE HANDLER (MANDATORY)

File: `tgbot/handlers/voice.py` (NEW FILE)

```python
import base64
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle incoming voice messages:
    1. Download voice file from Telegram
    2. Base64-encode the audio
    3. Forward to AI Agent /api/voice
    4. Reply with agent response
    """
    voice = update.message.voice
    if voice is None:
        return

    user_id = update.effective_user.id
    session_id = f"tg_{user_id}"
    chat_id = update.effective_chat.id

    logger.info(
        "Voice message received: session_id=%s, duration=%d, file_size=%s, mime_type=%s",
        session_id,
        voice.duration,
        voice.file_size,
        voice.mime_type,
    )

    backend_client = context.bot_data["backend_client"]

    try:
        # 1. Download voice file from Telegram
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await voice_file.download_as_bytearray()

        # 2. Base64-encode
        audio_base64 = base64.b64encode(bytes(audio_bytes)).decode("utf-8")
        mime_type = voice.mime_type or "audio/ogg"

        logger.info(
            "Voice file downloaded: session_id=%s, size_bytes=%d",
            session_id,
            len(audio_bytes),
        )

        # 3. Forward to agent
        result = await backend_client.forward_voice(session_id, audio_base64, mime_type)

        # 4. Reply to user
        response_text = result.get("response", "")
        if not response_text:
            response_text = "Could not process voice message."

        await context.bot.send_message(chat_id=chat_id, text=response_text)

    except ValueError as e:
        if "AGENT_API_URL is not configured" in str(e):
            await context.bot.send_message(
                chat_id=chat_id,
                text="AGENT_API_URL is not configured",
            )
        else:
            logger.error("Voice forward error: session_id=%s, error=%s", session_id, e)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Backend unavailable, please try again later.",
            )
    except Exception as e:
        logger.error("Voice handler error: session_id=%s, error=%s", session_id, e)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Backend unavailable, please try again later.",
        )
```

Rules:
- Error messages MUST be identical to text message handler (v18): "Backend unavailable, please try again later."
- Configuration error MUST be identical: "AGENT_API_URL is not configured"
- MUST use `context.bot.get_file(file_id)` для загрузки файла
- MUST use `download_as_bytearray()` для получения bytes
- MUST NOT log audio content (OK: session_id, duration, file_size, mime_type)
- `voice.mime_type` fallback: `"audio/ogg"` (Telegram default for voice)

---

### DISPATCHER — HANDLER REGISTRATION (MANDATORY)

File: `tgbot/dispatcher.py`

Add voice handler registration:

```python
from telegram.ext import MessageHandler, filters
from tgbot.handlers.voice import handle_voice_message

def setup_handlers(application, backend_client, diagnostics) -> None:
    # ... existing handler registrations ...

    # Register voice message handler (NEW)
    application.add_handler(
        MessageHandler(filters.VOICE, handle_voice_message)
    )
```

Rules:
- MUST register AFTER text message handler
- MUST use `filters.VOICE` (not `filters.AUDIO` — AUDIO is for audio files, VOICE is for voice messages)
- `backend_client` MUST be passed via `context.bot_data` (same pattern as text handler)

---

### BOT — FILES TO MODIFY/CREATE (MANDATORY)

| File | Action | Change |
|------|--------|--------|
| `tgbot/handlers/voice.py` | CREATE | Voice message handler |
| `tgbot/handlers/__init__.py` | CREATE (if absent) | Empty init |
| `tgbot/services/backend_client.py` | MODIFY | Add `forward_voice()` method |
| `tgbot/dispatcher.py` | MODIFY | Register voice handler |

---

### BOT — NEW TESTS (MANDATORY)

File: `tests/test_voice_handler.py` (NEW)

```python
# Required test cases:

# test_voice_handler_forwards_to_agent
#   Mock voice update → downloads file → calls forward_voice → replies with response

# test_voice_handler_no_agent_url
#   AGENT_API_URL not configured → replies "AGENT_API_URL is not configured"

# test_voice_handler_agent_error
#   forward_voice raises → replies "Backend unavailable..."

# test_voice_handler_download_error
#   get_file raises → replies "Backend unavailable..."
```

File: `tests/test_backend_client.py` (extend existing)

```python
# Required additional test cases:

# test_forward_voice_success
#   Mock HTTP response → returns {response, transcription}

# test_forward_voice_no_agent_url
#   agent_api_url=None → raises ValueError

# test_forward_voice_agent_error
#   Mock 500 → raises after retries
```

---

## ENVIRONMENT VARIABLES

### No New Env Vars Required

Все необходимые переменные уже определены в базовых спецификациях:

| Variable | Service | Defined In | Purpose |
|----------|---------|------------|---------|
| `AGENT_API_URL` | Bot | SPEC v18 | URL AI Agent сервиса |
| `MODEL_API_KEY` | Agent | SPEC ai-agent-v1 | Gemini API key |
| `MODEL_NAME` | Agent | SPEC ai-agent-v1 | Gemini model (default: gemini-2.0-flash-exp) |

### AGENT_API_URL Configuration (MANDATORY)

Для работы текстовых И голосовых сообщений, бот MUST иметь `AGENT_API_URL` указывающий
на задеплоенный AI Agent сервис.

При деплое бота через `deploy-bot.sh`:
```bash
# Добавить в ENV_VARS:
AGENT_API_URL=https://ai-agent-298607833444.europe-west4.run.app
```

Или через `--set-env-vars`:
```bash
gcloud run deploy telegram-bot \
    --set-env-vars="AGENT_API_URL=https://ai-agent-298607833444.europe-west4.run.app" \
    ...
```

---

## GEMINI MULTIMODAL — TECHNICAL DETAILS

### Supported Audio Formats

Gemini API поддерживает следующие аудио форматы через `inline_data`:
- `audio/ogg` (Telegram voice messages — OGG/Opus)
- `audio/mpeg` (MP3)
- `audio/wav` (WAV)
- `audio/webm` (WebM)

### Request Size Limits

- Gemini API `inline_data` limit: ~20MB base64 (≈15MB decoded audio)
- Telegram voice messages: max 1 minute by default, larger with Telegram Premium
- Typical voice message: 50KB–500KB → well within limits
- Agent SHOULD reject audio_base64 > 20MB with HTTP 400

### Model Compatibility

- `gemini-2.0-flash-exp` — поддерживает multimodal audio input
- `gemini-1.5-flash` — поддерживает multimodal audio input
- `gemini-1.5-pro` — поддерживает multimodal audio input
- Model MUST support multimodal audio; text-only models will return errors

---

## DEPLOYMENT SEQUENCE (MANDATORY)

### Step 1: Deploy updated AI Agent

```bash
cd ai-agent/
# Implement agent-side changes (new endpoint, LLM method, processor method)
# Run tests
pytest tests/
# Deploy
./deploy-agent.sh
```

### Step 2: Verify agent voice endpoint

```bash
# Quick smoke test with empty audio (should return 400)
curl -s -X POST https://ai-agent-298607833444.europe-west4.run.app/api/voice \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"test_123","audio_base64":"","mime_type":"audio/ogg"}'
# Expected: {"error":"session_id and audio_base64 are required"}
```

### Step 3: Deploy updated Telegram Bot

```bash
cd telegram-bot/
# Implement bot-side changes (voice handler, backend_client method, dispatcher)
# Run tests
pytest tests/
# Deploy with AGENT_API_URL
export AGENT_API_URL=https://ai-agent-298607833444.europe-west4.run.app
./deploy-bot.sh
```

### Step 4: End-to-end verification

1. Open Telegram → send text message → verify text response from AI
2. Open Telegram → send voice message → verify text response from AI
3. Check Cloud Run logs for both services — no secrets, no audio content in logs

---

## SELF-CHECKS (MANDATORY)

### Agent-side
- [ ] `POST /api/voice` endpoint exists and accepts JSON
- [ ] `LLMClient.generate_response_from_audio()` builds correct Gemini multimodal request
- [ ] `inline_data` содержит `mime_type` и `data` (base64)
- [ ] Response parsing handles both marker format and fallback
- [ ] `_parse_voice_response()` не бросает исключений при неожиданном формате
- [ ] `MessageProcessor.process_voice()` validates non-empty audio
- [ ] Error responses masked (no API keys in error messages)
- [ ] Logs не содержат audio content
- [ ] All new tests pass

### Bot-side
- [ ] Voice handler registered in dispatcher with `filters.VOICE`
- [ ] Handler downloads file via `bot.get_file()` + `download_as_bytearray()`
- [ ] Handler base64-encodes audio correctly
- [ ] `BackendClient.forward_voice()` POSTs to `/api/voice`
- [ ] Retry policy identical to `forward_message()`
- [ ] Error messages identical to text handler ("Backend unavailable...")
- [ ] Logs не содержат audio content
- [ ] All new tests pass

### Integration
- [ ] `AGENT_API_URL` configured on bot → bot can reach agent
- [ ] Text messages work end-to-end
- [ ] Voice messages work end-to-end
- [ ] Agent starts without MODEL_API_KEY → voice returns "not configured" message

---

## DEFINITION OF DONE

- All self-checks passed
- Text messages forwarded from bot to agent and back
- Voice messages forwarded from bot to agent, transcribed, response returned
- No secrets or audio content in logs
- All tests pass on both services
- Both services deployed to Cloud Run

---

END OF SPEC
