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
- Ingress: `internal` (accessible only from within the VPC)
- The Telegram bot Cloud Run service MUST use Direct VPC Egress with `vpc-egress=all-traffic` to route requests to master-agent through the VPC

#### Scenario: telegram-bot reaches master-agent via VPC
- **WHEN** telegram-bot sends a request to master-agent URL
- **THEN** the request SHALL be routed through the VPC (Direct VPC Egress)
- **AND** master-agent with `ingress=internal` SHALL accept the request

#### Scenario: Direct internet access to master-agent blocked
- **WHEN** an external client attempts to reach master-agent directly from the internet
- **THEN** master-agent SHALL reject the request (Cloud Run returns 404)

### Requirement: Deploy script configuration
The `deploy-bot.sh` script SHALL include a compile-time default for `AGENT_API_URL` so the bot always has a valid URL even when the env var is not explicitly provided at deploy time.

When deploying:
1. If `AGENT_API_URL` is provided via env → use that value
2. If not provided → use the compile-time default baked into the script
3. Include `--vpc-egress=all-traffic` flag on every deploy
4. After deploy, grant the bot's service account `roles/run.invoker` on master-agent (idempotent)

#### Scenario: Deployment without explicit AGENT_API_URL
- **WHEN** deploying without setting `AGENT_API_URL` env var
- **THEN** the deployed service SHALL still have `AGENT_API_URL` set to the compile-time default
- **AND** message forwarding SHALL work without any manual configuration

#### Scenario: VPC egress set on every deploy
- **WHEN** `deploy-bot.sh` runs
- **THEN** the Cloud Run service SHALL be deployed with `--vpc-egress=all-traffic`
- **AND** all outbound traffic from the bot SHALL route through the VPC

#### Scenario: IAM binding applied on every deploy
- **WHEN** `deploy-bot.sh` completes deployment
- **THEN** the script SHALL call `gcloud run services add-iam-policy-binding master-agent` granting the bot SA `roles/run.invoker`
- **AND** the operation SHALL be idempotent (safe to run multiple times)

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
