## ADDED Requirements

### Requirement: Agent URL resolution order

The system SHALL resolve the agent API URL in the following order:
1. `AGENT_API_URL` environment variable (if set and non-empty after sanitization)
2. Internal Cloud Run DNS URL: `https://master-agent.{region}.run.internal`

The function SHALL always return a URL (never None).

#### Scenario: Environment variable takes priority
- **WHEN** `AGENT_API_URL` environment variable is set to `https://custom-agent.example.com`
- **THEN** the system SHALL return `https://custom-agent.example.com`

#### Scenario: Fallback to Internal DNS
- **WHEN** `AGENT_API_URL` environment variable is not set
- **AND** region is `europe-west4`
- **THEN** the system SHALL return `https://master-agent.europe-west4.run.internal`

#### Scenario: Empty environment variable triggers fallback
- **WHEN** `AGENT_API_URL` environment variable is set to empty string or whitespace
- **AND** region is `europe-west4`
- **THEN** the system SHALL return `https://master-agent.europe-west4.run.internal`

### Requirement: Internal DNS URL format

The Internal DNS URL SHALL be constructed as:
```
https://master-agent.{region}.run.internal
```

Where:
- Protocol: always `https`
- Service name: hardcoded `master-agent`
- Region: from `get_region()` function
- Domain: `run.internal`

#### Scenario: URL construction
- **WHEN** constructing Internal DNS URL
- **AND** `get_region()` returns `us-central1`
- **THEN** the system SHALL return `https://master-agent.us-central1.run.internal`

### Requirement: No external dependencies

The agent URL resolution SHALL NOT require:
- External API calls
- SDK initialization
- Network requests
- IAM permissions

Resolution SHALL be pure string manipulation using existing configuration.

#### Scenario: Offline resolution
- **WHEN** resolving agent URL without network access
- **AND** `AGENT_API_URL` is not set
- **THEN** the system SHALL still return the Internal DNS URL without errors
