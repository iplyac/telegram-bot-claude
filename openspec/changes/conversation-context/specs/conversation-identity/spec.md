## ADDED Requirements

### Requirement: Conversation ID derivation

The system SHALL derive conversation_id based on Telegram chat type.

#### Scenario: Private chat (DM)
- **WHEN** message is received from a private chat
- **THEN** conversation_id SHALL be `tg_dm_{user_id}`

#### Scenario: Group chat
- **WHEN** message is received from a group chat
- **THEN** conversation_id SHALL be `tg_group_{chat_id}`

#### Scenario: Supergroup chat
- **WHEN** message is received from a supergroup
- **THEN** conversation_id SHALL be `tg_group_{chat_id}`

#### Scenario: Unknown chat type
- **WHEN** chat type is not recognized
- **THEN** conversation_id SHALL be `tg_chat_{chat_id}`

### Requirement: Request format to master-agent

The system SHALL send requests to master-agent in the new format with conversation_id and metadata.

#### Scenario: Text message request format
- **WHEN** forwarding a text message to master-agent
- **THEN** request body SHALL contain:
  - `conversation_id`: derived conversation identifier
  - `message`: user message text
  - `metadata.telegram.chat_id`: Telegram chat ID (integer)
  - `metadata.telegram.user_id`: Telegram user ID (integer)
  - `metadata.telegram.chat_type`: one of "private", "group", "supergroup"

#### Scenario: Voice message request format
- **WHEN** forwarding a voice message to master-agent
- **THEN** request body SHALL contain:
  - `conversation_id`: derived conversation identifier
  - `audio_base64`: base64-encoded audio
  - `mime_type`: audio MIME type
  - `metadata.telegram.chat_id`: Telegram chat ID (integer)
  - `metadata.telegram.user_id`: Telegram user ID (integer)
  - `metadata.telegram.chat_type`: one of "private", "group", "supergroup"

### Requirement: Stateless bot design

The Telegram bot SHALL NOT store conversation state.

#### Scenario: No conversation storage
- **WHEN** processing any message
- **THEN** the bot SHALL NOT persist conversation history
- **AND** the bot SHALL NOT maintain session state between requests

#### Scenario: No LLM awareness
- **WHEN** processing any message
- **THEN** the bot SHALL NOT be aware of LLM provider details
- **AND** the bot SHALL NOT generate LLM-specific identifiers

### Requirement: Master-agent backward compatibility

Master-agent SHALL support both old and new request formats.

#### Scenario: New format request
- **WHEN** request contains `conversation_id` field
- **THEN** master-agent SHALL use `conversation_id` for session management
- **AND** master-agent SHALL read metadata from `metadata.telegram`

#### Scenario: Old format request (deprecated)
- **WHEN** request contains `session_id` field but no `conversation_id`
- **THEN** master-agent SHALL use `session_id` as conversation identifier
- **AND** master-agent SHALL log deprecation warning

### Requirement: Error handling

The system SHALL handle errors without altering conversation identity.

#### Scenario: Master-agent unavailable
- **WHEN** master-agent returns error or is unreachable
- **THEN** the bot SHALL return generic error message to user
- **AND** the bot SHALL NOT retry with different conversation_id
