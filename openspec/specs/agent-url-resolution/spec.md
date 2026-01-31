## ADDED Requirements

### Requirement: Agent URL from environment variable

The system SHALL resolve the agent API URL from the `AGENT_API_URL` environment variable.

The `AGENT_API_URL` MUST be set to the public Cloud Run URL of master-agent:
```
https://master-agent-<hash>.<region>.a.run.app
```

#### Scenario: Environment variable set
- **WHEN** `AGENT_API_URL` environment variable is set to `https://master-agent-xxx.europe-west4.a.run.app`
- **THEN** the system SHALL return `https://master-agent-xxx.europe-west4.a.run.app`

#### Scenario: Environment variable not set
- **WHEN** `AGENT_API_URL` environment variable is not set
- **THEN** the system SHALL return `None`
- **AND** message handling SHALL reply with "AGENT_API_URL is not configured"

#### Scenario: Empty environment variable
- **WHEN** `AGENT_API_URL` environment variable is set to empty string
- **THEN** the system SHALL return empty string (falsy value)
- **AND** message handling SHALL treat it as not configured

#### Scenario: Whitespace-only environment variable
- **WHEN** `AGENT_API_URL` environment variable is set to whitespace only (e.g., `"   "`)
- **THEN** the system SHALL return `None`

### Requirement: URL sanitization

The system SHALL sanitize the `AGENT_API_URL` value by:
- Stripping leading/trailing whitespace
- Removing control characters (ASCII 0-31 and 127)

#### Scenario: Whitespace trimmed
- **WHEN** `AGENT_API_URL` is set to `  https://example.com  `
- **THEN** the system SHALL return `https://example.com`

### Requirement: No internal DNS fallback

The system SHALL NOT attempt to construct internal DNS URLs (`.run.internal`).

Rationale: Cloud Run does not natively support `.run.internal` DNS resolution.
This is a community convention (runsd project), not an official Google Cloud feature.

#### Scenario: No fallback URL construction
- **WHEN** `AGENT_API_URL` is not set
- **THEN** the system SHALL NOT construct `https://master-agent.{region}.run.internal`
- **AND** the system SHALL return `None`

## Infrastructure Requirements

### Requirement: master-agent accessibility

The master-agent Cloud Run service MUST be configured with:
- Ingress: `all` (publicly accessible)
- URL format: `https://master-agent-<hash>.<region>.a.run.app`

#### Scenario: telegram-bot reaches master-agent
- **WHEN** telegram-bot sends request to master-agent public URL
- **THEN** request SHALL succeed over HTTPS

### Requirement: Deploy script configuration

The `deploy-bot.sh` script SHALL support `AGENT_API_URL` environment variable.

When deploying:
1. If `AGENT_API_URL` is provided → include in Cloud Run env vars
2. If not provided → deployment proceeds, but bot cannot forward messages

#### Scenario: Deployment with AGENT_API_URL
- **WHEN** deploying with `AGENT_API_URL=https://master-agent-xxx.run.app ./deploy-bot.sh`
- **THEN** the deployed service SHALL have `AGENT_API_URL` environment variable set

### Requirement: Automatic webhook setup

The deploy script SHALL automatically configure the Telegram webhook after deployment.

Configuration:
1. Retrieve bot token from Secret Manager (`TELEGRAM_BOT_TOKEN`)
2. Derive webhook secret: `sha256(bot_token)[:32]`
3. Construct webhook URL: `{service_url}/telegram/webhook`
4. Call Telegram API `setWebhook` with `url` and `secret_token`

#### Scenario: Webhook auto-configuration
- **WHEN** deploy-bot.sh completes deployment
- **THEN** the script SHALL call Telegram setWebhook API
- **AND** the webhook URL SHALL be the Cloud Run service URL + `/telegram/webhook`
- **AND** the secret_token SHALL be derived from bot token (sha256, first 32 hex chars)

#### Scenario: Webhook secret validation
- **WHEN** Telegram sends webhook request
- **THEN** the bot SHALL validate `X-Telegram-Bot-Api-Secret-Token` header
- **AND** reject requests with invalid or missing secret
