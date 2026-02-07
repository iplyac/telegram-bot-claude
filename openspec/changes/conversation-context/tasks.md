## 1. Telegram Bot: Conversation ID logic

- [x] 1.1 Create `derive_conversation_id(update)` function in dispatcher.py
- [x] 1.2 Handle private chat → `tg_dm_{user_id}`
- [x] 1.3 Handle group/supergroup → `tg_group_{chat_id}`
- [x] 1.4 Handle unknown chat type → `tg_chat_{chat_id}`

## 2. Telegram Bot: Update request format

- [x] 2.1 Create `TelegramMetadata` dataclass/dict structure
- [x] 2.2 Update `BackendClient.forward_message()` signature
- [x] 2.3 Update `BackendClient.forward_voice()` signature
- [x] 2.4 Change payload: `session_id` → `conversation_id`
- [x] 2.5 Add `metadata.telegram` to payload

## 3. Telegram Bot: Update handlers

- [x] 3.1 Update `_handle_text_message` to use new format
- [x] 3.2 Update `handle_voice_message` to use new format
- [x] 3.3 Update logging to include conversation_id and chat_type

## 4. Master Agent: API compatibility (separate repo)

- [x] 4.1 Update `/api/chat` to accept new format
- [x] 4.2 Update `/api/voice` to accept new format
- [x] 4.3 Add backward compatibility for old `session_id` format
- [x] 4.4 Log deprecation warning for old format

## 5. Testing

- [ ] 5.1 Test private chat conversation_id derivation
- [ ] 5.2 Test group chat conversation_id derivation
- [ ] 5.3 Test end-to-end message flow with new format
- [ ] 5.4 Test backward compatibility with old format
