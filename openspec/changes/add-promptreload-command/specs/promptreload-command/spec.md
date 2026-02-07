## ADDED Requirements

### Requirement: Bot responds to /promptreload command
The bot SHALL respond to the `/promptreload` command.

#### Scenario: User sends /promptreload
- **WHEN** user sends `/promptreload` command
- **THEN** bot calls master-agent `POST /api/reload-prompt` endpoint
- **AND** bot replies with the result

### Requirement: Display success message
The bot SHALL display success message when prompt is reloaded.

#### Scenario: Prompt reload succeeds
- **WHEN** master-agent returns `{"status": "ok", "prompt_length": N}`
- **THEN** bot replies with "Prompt reloaded successfully (N characters)"

### Requirement: Display error message from API
The bot SHALL display error message when API returns error status.

#### Scenario: API returns error status
- **WHEN** master-agent returns `{"status": "error", "error": "AGENT_PROMPT_ID not configured"}`
- **THEN** bot replies with "Failed to reload prompt: AGENT_PROMPT_ID not configured"

### Requirement: Handle backend errors gracefully
The bot SHALL handle error conditions with user-friendly messages.

#### Scenario: Backend not configured
- **WHEN** AGENT_API_URL environment variable is not set
- **THEN** bot replies with "Prompt reload unavailable - backend not configured"

#### Scenario: HTTP request fails
- **WHEN** HTTP request to master-agent fails (timeout, connection error, non-2xx status)
- **THEN** bot replies with "Failed to reload prompt" and error details
