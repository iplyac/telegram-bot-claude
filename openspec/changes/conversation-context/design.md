## Context

Текущий формат запроса к master-agent:
```json
{
  "session_id": "tg_123456",
  "message": "Hello"
}
```

Проблемы:
- Не различает личные сообщения и группы
- Нет metadata о Telegram контексте
- Master-agent не знает тип чата

## Goals / Non-Goals

**Goals:**
- Стабильный conversation_id для DM и групп
- Передача Telegram metadata в master-agent
- Обратная совместимость API

**Non-Goals:**
- Хранение истории в telegram-bot (stateless)
- LLM-специфичная логика в боте
- Изменение поведения master-agent (только API контракт)

## Decisions

### 1. Формат conversation_id

**Решение:**
- Private chat: `tg_dm_{user_id}`
- Group/Supergroup: `tg_group_{chat_id}`

**Обоснование:**
- Префикс `tg_` — источник (Telegram)
- `dm_` / `group_` — тип чата
- ID — стабильный идентификатор

### 2. Новый формат запроса

**Решение:**
```json
{
  "conversation_id": "tg_dm_123456",
  "message": "Hello",
  "metadata": {
    "telegram": {
      "chat_id": 123456,
      "user_id": 789012,
      "chat_type": "private"
    }
  }
}
```

**Обоснование:**
- `conversation_id` — главный идентификатор для master-agent
- `metadata.telegram` — дополнительный контекст
- Числовые ID (не строки) для chat_id/user_id

### 3. Обратная совместимость

**Решение:** Master-agent поддерживает оба формата:
- Новый: `conversation_id` + `metadata`
- Старый: `session_id` + `message` (deprecated)

**Миграция:**
1. Обновить master-agent для поддержки обоих форматов
2. Обновить telegram-bot на новый формат
3. (Опционально) Удалить старый формат позже

### 4. chat_type значения

**Решение:**
- `"private"` — личные сообщения
- `"group"` — обычная группа
- `"supergroup"` — супергруппа

**Обоснование:** Соответствует Telegram API.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Breaking change API | Обратная совместимость в master-agent |
| Групповые чаты — много пользователей | conversation_id по chat_id, не user_id |
| Неизвестный chat_type | Fallback на `tg_chat_{chat_id}` |
