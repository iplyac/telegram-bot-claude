# Инструкция: Добавление Voice Integration в AI Agent

**Базовая спецификация:** SPEC_ai-agent_v1.md
**Дополнительная спецификация:** SPEC_voice_integration_v1.md
**Дата:** 2026-01-28

---

## ЦЕЛЬ

Добавить поддержку обработки голосовых сообщений в AI Agent сервис:
- Новый endpoint `POST /api/voice`
- Транскрипция аудио через Gemini multimodal API
- Генерация ответа на транскрибированный текст

---

## ИЗМЕНЕНИЯ В ФАЙЛАХ

| Файл | Действие | Описание |
|------|----------|----------|
| `app.py` | MODIFY | Добавить endpoint `POST /api/voice` |
| `agent/llm_client.py` | MODIFY | Добавить `generate_response_from_audio()` и `_parse_voice_response()` |
| `agent/processor.py` | MODIFY | Добавить `process_voice()` |
| `tests/test_voice_api.py` | CREATE | Тесты для voice endpoint |
| `tests/test_llm_client.py` | MODIFY | Добавить тесты для voice методов |

---

## 1. ИЗМЕНЕНИЯ В `agent/llm_client.py`

### 1.1 Добавить метод `generate_response_from_audio`

```python
async def generate_response_from_audio(
    self, audio_base64: str, mime_type: str, session_id: str
) -> dict:
    """
    Send audio to Gemini multimodal API for transcription + response.

    Args:
        audio_base64: Base64-encoded audio bytes
        mime_type: Audio MIME type (e.g., "audio/ogg")
        session_id: Session ID for logging

    Returns:
        dict with keys: "response", "transcription"
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
        "LLM voice request",
        extra={
            "session_id": session_id,
            "audio_size": audio_size,
            "mime_type": mime_type,
            "model": self.model_name,
        },
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
            "LLM voice response",
            extra={
                "session_id": session_id,
                "transcription_length": len(result["transcription"]),
                "response_length": len(result["response"]),
            },
        )
        return result

    except httpx.TimeoutException as e:
        error_msg = mask_token(str(e))
        logger.error("LLM voice timeout: %s", error_msg, extra={"session_id": session_id})
        raise RuntimeError(f"LLM request timed out: {error_msg}") from e
    except httpx.HTTPStatusError as e:
        error_msg = mask_token(str(e))
        logger.error(
            "LLM voice HTTP error",
            extra={"session_id": session_id, "status": e.response.status_code},
        )
        raise RuntimeError(f"LLM API error: {error_msg}") from e
    except Exception as e:
        error_msg = mask_token(str(e))
        logger.error("LLM voice error: %s", error_msg, extra={"session_id": session_id})
        raise RuntimeError(f"LLM error: {error_msg}") from e
```

### 1.2 Добавить метод `_parse_voice_response`

```python
@staticmethod
def _parse_voice_response(raw_text: str) -> dict:
    """
    Parse Gemini response containing [TRANSCRIPTION] and [RESPONSE] markers.
    Falls back to using full text as response if markers not found.

    Args:
        raw_text: Raw response text from Gemini

    Returns:
        dict with "response" and "transcription" keys
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

### 1.3 Требования к реализации

- `mask_token()` ДОЛЖЕН быть доступен (уже должен быть в файле согласно SPEC_ai-agent_v1)
- `self.endpoint` ДОЛЖЕН быть Gemini API endpoint (default: `https://generativelanguage.googleapis.com/v1beta/models`)
- `self.model_name` ДОЛЖЕН поддерживать multimodal (gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro)
- Timeout ДОЛЖЕН быть 25s (уже настроен в constructor)

---

## 2. ИЗМЕНЕНИЯ В `agent/processor.py`

### 2.1 Добавить метод `process_voice`

```python
async def process_voice(self, session_id: str, audio_base64: str, mime_type: str) -> dict:
    """
    Process a voice message and return transcription + response.

    Args:
        session_id: Session identifier
        audio_base64: Base64-encoded audio bytes
        mime_type: Audio MIME type

    Returns:
        dict with "response" and "transcription" keys

    Raises:
        RuntimeError: If processing fails
    """
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
        logger.error("Voice processing error", extra={"session_id": session_id, "error": str(e)})
        raise RuntimeError("Failed to process voice message") from e
```

---

## 3. ИЗМЕНЕНИЯ В `app.py`

### 3.1 Добавить endpoint `POST /api/voice`

Добавить ПОСЛЕ существующего endpoint `/api/chat`:

```python
@app.post("/api/voice")
async def voice(request: Request):
    """
    Process voice message via Gemini multimodal API.

    Request JSON:
    {
        "session_id": "tg_<user_id>",
        "audio_base64": "<base64-encoded-audio>",
        "mime_type": "audio/ogg"
    }

    Response JSON:
    {
        "response": "<agent_reply>",
        "transcription": "<transcribed_text>"
    }
    """
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

    # Log request (without audio content)
    audio_size = len(audio_base64) * 3 // 4
    logger.info(
        "Voice API request",
        extra={
            "session_id": session_id,
            "audio_size": audio_size,
            "mime_type": mime_type,
        },
    )

    try:
        processor: MessageProcessor = request.app.state.processor
        result = await processor.process_voice(session_id, audio_base64, mime_type)
        return result
    except Exception as e:
        error_msg = mask_token(str(e))
        logger.error("Voice API error", extra={"session_id": session_id, "error": error_msg})
        return JSONResponse(
            status_code=500,
            content={"error": "Agent unavailable, please try again later"},
        )
```

### 3.2 Требования

- `mask_token()` ДОЛЖЕН быть импортирован/доступен в app.py
- `JSONResponse` ДОЛЖЕН быть импортирован из fastapi.responses
- `MessageProcessor` ДОЛЖЕН быть импортирован для type hint

---

## 4. НОВЫЙ ФАЙЛ `tests/test_voice_api.py`

```python
"""Tests for voice API endpoint."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch("app.config") as mock:
        mock.get_project_id.return_value = "test-project"
        mock.get_log_level.return_value = "INFO"
        mock.get_model_api_key.return_value = "test-api-key"
        mock.get_model_name.return_value = "gemini-2.0-flash-exp"
        mock.get_model_endpoint.return_value = None
        mock.get_port.return_value = 8080
        yield mock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    with patch("app.LLMClient") as mock_class:
        mock_instance = MagicMock()
        mock_instance.close = AsyncMock()
        mock_instance.generate_response_from_audio = AsyncMock(
            return_value={"response": "Test response", "transcription": "Test transcription"}
        )
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def client(mock_config, mock_llm_client):
    """Create test client."""
    from app import app
    with TestClient(app) as client:
        yield client


def test_voice_endpoint_valid_contract(client, mock_llm_client):
    """POST /api/voice with valid data should return response and transcription."""
    payload = {
        "session_id": "tg_123456",
        "audio_base64": "dGVzdCBhdWRpbyBkYXRh",  # "test audio data" in base64
        "mime_type": "audio/ogg",
    }

    response = client.post("/api/voice", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "transcription" in data


def test_voice_endpoint_missing_api_key(client):
    """Voice endpoint with no API key should return configured error message."""
    with patch("app.config.get_model_api_key", return_value=None):
        payload = {
            "session_id": "tg_123456",
            "audio_base64": "dGVzdA==",
            "mime_type": "audio/ogg",
        }

        response = client.post("/api/voice", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "not configured" in data.get("response", "").lower()


def test_voice_endpoint_missing_audio(client):
    """Voice endpoint with missing audio should return 400."""
    payload = {
        "session_id": "tg_123456",
        "mime_type": "audio/ogg",
    }

    response = client.post("/api/voice", json=payload)

    assert response.status_code == 400
    assert "required" in response.json().get("error", "").lower()


def test_voice_endpoint_missing_session_id(client):
    """Voice endpoint with missing session_id should return 400."""
    payload = {
        "audio_base64": "dGVzdA==",
        "mime_type": "audio/ogg",
    }

    response = client.post("/api/voice", json=payload)

    assert response.status_code == 400


def test_voice_endpoint_invalid_json(client):
    """Voice endpoint with invalid JSON should return 400."""
    response = client.post(
        "/api/voice",
        content="not valid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "Invalid JSON" in response.json().get("error", "")


def test_voice_endpoint_timeout(client, mock_llm_client):
    """Voice endpoint timeout should return 500."""
    mock_llm_client.generate_response_from_audio = AsyncMock(
        side_effect=RuntimeError("Timeout")
    )

    payload = {
        "session_id": "tg_123456",
        "audio_base64": "dGVzdA==",
        "mime_type": "audio/ogg",
    }

    response = client.post("/api/voice", json=payload)

    assert response.status_code == 500
    assert "unavailable" in response.json().get("error", "").lower()
```

---

## 5. ДОПОЛНЕНИЯ В `tests/test_llm_client.py`

Добавить тесты:

```python
def test_llm_client_voice_no_api_key():
    """Voice with no API key should return not configured message."""
    client = LLMClient(api_key=None, model_name="gemini-2.0-flash-exp", endpoint=None)

    import asyncio
    result = asyncio.run(client.generate_response_from_audio("dGVzdA==", "audio/ogg", "test_session"))

    assert result["response"] == "AI model not configured. Please contact administrator."
    assert result["transcription"] == ""


def test_parse_voice_response_with_markers():
    """Parse response with [TRANSCRIPTION] and [RESPONSE] markers."""
    raw = "[TRANSCRIPTION]\nHello world\n[RESPONSE]\nHi there!"

    result = LLMClient._parse_voice_response(raw)

    assert result["transcription"] == "Hello world"
    assert result["response"] == "Hi there!"


def test_parse_voice_response_fallback():
    """Parse response without markers should use full text as response."""
    raw = "This is just a plain response"

    result = LLMClient._parse_voice_response(raw)

    assert result["transcription"] == ""
    assert result["response"] == "This is just a plain response"
```

---

## 6. SELF-CHECKS

После реализации проверить:

- [ ] `POST /api/voice` endpoint существует и принимает JSON
- [ ] Request validation: 400 при отсутствии session_id или audio_base64
- [ ] `LLMClient.generate_response_from_audio()` корректно формирует Gemini multimodal request
- [ ] `inline_data` содержит `mime_type` и `data` (base64)
- [ ] `_parse_voice_response()` обрабатывает оба формата (с маркерами и без)
- [ ] `MessageProcessor.process_voice()` валидирует non-empty audio
- [ ] Error messages замаскированы (без API keys)
- [ ] Логи НЕ содержат audio content
- [ ] Сервис стартует без API key и возвращает "not configured" message
- [ ] Все новые тесты проходят

---

## 7. DEPLOYMENT

После реализации:

```bash
cd ai-agent/
pytest tests/ -v
./deploy-agent.sh
```

Проверка endpoint:

```bash
# Должен вернуть 400 (missing fields)
curl -s -X POST https://ai-agent-298607833444.europe-west4.run.app/api/voice \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"test"}'

# Expected: {"error":"session_id and audio_base64 are required"}
```

---

## 8. ОБНОВЛЕНИЯ ДЛЯ SPEC_ai-agent_v2

Рекомендуемые изменения для включения в следующую версию спецификации:

### 8.1 FASTAPI ENDPOINTS

Добавить:
```
- POST /api/voice -> Voice processing endpoint (see VOICE API CONTRACT)
```

### 8.2 VOICE API CONTRACT (NEW SECTION)

```markdown
## VOICE API CONTRACT (MANDATORY)

### POST /api/voice

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
- MUST return HTTP 400 on missing/invalid fields
- MUST return HTTP 500 on processing error
- MUST complete within 30 seconds
- MUST be safe to retry (stateless)
- Supported mime_types: audio/ogg, audio/mpeg, audio/wav, audio/webm
- MUST NOT log audio content (OK: session_id, audio size, mime_type)
```

### 8.3 LLM CLIENT MODULE

Добавить методы:
```markdown
- async generate_response_from_audio(self, audio_base64: str, mime_type: str, session_id: str) -> dict
  - If api_key is None → return {"response": "not configured...", "transcription": ""}
  - Call Gemini multimodal API with inline_data
  - Parse response for [TRANSCRIPTION] and [RESPONSE] markers
  - On error: raise RuntimeError with masked message

- @staticmethod _parse_voice_response(raw_text: str) -> dict
  - Parse markers if present, otherwise fallback to full text as response
  - MUST NOT raise on unexpected format
```

### 8.4 PROCESSOR MODULE

Добавить метод:
```markdown
- async process_voice(self, session_id: str, audio_base64: str, mime_type: str) -> dict
  - Validate non-empty audio
  - Call llm_client.generate_response_from_audio()
  - Return dict with response and transcription
```

### 8.5 TESTS

Добавить файл:
```
tests/test_voice_api.py
```

Добавить тесты в test_llm_client.py:
```
- test_llm_client_voice_no_api_key
- test_llm_client_voice_success
- test_parse_voice_response_with_markers
- test_parse_voice_response_fallback
```

### 8.6 SELF-CHECKS

Добавить:
```
- POST /api/voice endpoint exists and validates input
- generate_response_from_audio() builds correct Gemini multimodal request
- _parse_voice_response() handles both marker and fallback formats
- Audio content not logged
- Voice tests pass
```

---

END OF INSTRUCTION
