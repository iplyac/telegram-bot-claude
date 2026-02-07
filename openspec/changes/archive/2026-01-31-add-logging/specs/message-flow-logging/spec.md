## ADDED Requirements

### Requirement: JSON structured logging

The system SHALL output logs in JSON format compatible with Google Cloud Logging.

#### Scenario: Log entry format
- **WHEN** any log message is emitted
- **THEN** it SHALL be formatted as a single-line JSON object
- **AND** include fields: `timestamp`, `level`, `message`, `logger`

### Requirement: Correlation ID for message flow

The system SHALL generate a unique `request_id` for each incoming Telegram update to correlate all related log entries.

#### Scenario: Request ID generation
- **WHEN** a Telegram webhook request is received
- **THEN** the system SHALL generate a `request_id` in format `req_{8-char-hex}`
- **AND** include this `request_id` in all subsequent log entries for this request

#### Scenario: Request ID in logs
- **WHEN** logging any event related to a message flow
- **THEN** the log entry SHALL include `request_id` field

### Requirement: Message receive logging

The system SHALL log when a message is received from Telegram.

#### Scenario: Text message received
- **WHEN** a text message is received
- **THEN** the system SHALL log at INFO level with fields:
  - `request_id`
  - `user_id`
  - `update_id`
  - `message_type`: "text"
  - `message_length` (NOT message content for privacy)

#### Scenario: Voice message received
- **WHEN** a voice message is received
- **THEN** the system SHALL log at INFO level with fields:
  - `request_id`
  - `user_id`
  - `update_id`
  - `message_type`: "voice"
  - `audio_duration_seconds`

### Requirement: Agent request logging

The system SHALL log when forwarding a message to the agent API.

#### Scenario: Agent request start
- **WHEN** sending request to agent API
- **THEN** the system SHALL log at INFO level with fields:
  - `request_id`
  - `session_id`
  - `endpoint` (e.g., "/api/chat", "/api/voice")

#### Scenario: Agent response received
- **WHEN** response is received from agent API
- **THEN** the system SHALL log at INFO level with fields:
  - `request_id`
  - `status_code`
  - `latency_ms` (time from request start to response)

### Requirement: Reply sent logging

The system SHALL log when a reply is sent back to the user.

#### Scenario: Reply sent successfully
- **WHEN** reply message is sent to Telegram
- **THEN** the system SHALL log at INFO level with fields:
  - `request_id`
  - `user_id`
  - `latency_total_ms` (time from webhook received to reply sent)

### Requirement: Error logging

The system SHALL log errors with full context.

#### Scenario: Agent error
- **WHEN** agent API returns an error or times out
- **THEN** the system SHALL log at ERROR level with fields:
  - `request_id`
  - `error_type` (exception class name)
  - `error_message`
  - `session_id`

#### Scenario: Unexpected error
- **WHEN** an unexpected exception occurs
- **THEN** the system SHALL log at ERROR level with full traceback

### Requirement: Logging configuration

The system SHALL have centralized logging configuration.

#### Scenario: Log level from environment
- **WHEN** `LOG_LEVEL` environment variable is set
- **THEN** the system SHALL use that log level (DEBUG, INFO, WARNING, ERROR)

#### Scenario: Default log level
- **WHEN** `LOG_LEVEL` is not set
- **THEN** the system SHALL default to INFO level

#### Scenario: Library log suppression
- **WHEN** logging is configured
- **THEN** logs from `httpx` and `telegram` libraries SHALL be set to WARNING level
