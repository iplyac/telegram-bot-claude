## ADDED Requirements

### Requirement: Bot responds to /sessioninfo command
The bot SHALL respond to the `/sessioninfo` command in any chat (private or group).

#### Scenario: User sends /sessioninfo in private chat
- **WHEN** user sends `/sessioninfo` in a private chat
- **THEN** bot queries master-agent `/api/session-info` with conversation_id `tg_dm_{chat_id}`
- **AND** bot replies with session information

#### Scenario: User sends /sessioninfo in group chat
- **WHEN** user sends `/sessioninfo` in a group chat
- **THEN** bot queries master-agent `/api/session-info` with conversation_id `tg_group_{chat_id}`
- **AND** bot replies with session information

### Requirement: Display active session information
The bot SHALL display session details when a session exists.

#### Scenario: Session exists with message count
- **WHEN** master-agent returns `session_exists: true` and `message_count: N`
- **THEN** bot replies with formatted message containing conversation_id, session_id, status "Active", and message count

#### Scenario: Session exists without message count
- **WHEN** master-agent returns `session_exists: true` and `message_count: null`
- **THEN** bot replies with formatted message containing conversation_id, session_id, and status "Active" without message count

### Requirement: Display no session message
The bot SHALL inform user when no session exists.

#### Scenario: No active session
- **WHEN** master-agent returns `session_exists: false`
- **THEN** bot replies with message "No active session for this chat" and the conversation_id

### Requirement: Handle backend errors gracefully
The bot SHALL handle error conditions and provide user-friendly messages.

#### Scenario: Backend not configured
- **WHEN** AGENT_API_URL environment variable is not set
- **THEN** bot replies with "Session info unavailable - backend not configured"

#### Scenario: Backend request fails
- **WHEN** HTTP request to master-agent fails (timeout, connection error, non-2xx status)
- **THEN** bot replies with "Failed to get session info" and error details

#### Scenario: Backend returns invalid response
- **WHEN** master-agent returns response missing required fields
- **THEN** bot replies with "Failed to get session info: invalid response"
