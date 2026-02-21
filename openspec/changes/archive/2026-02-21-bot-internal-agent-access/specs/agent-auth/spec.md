## ADDED Requirements

### Requirement: Every request to master-agent carries an identity token
The system SHALL attach a Google Cloud ID token as a Bearer token in the `Authorization` header on every outbound HTTP request made by `BackendClient` to master-agent. The token audience SHALL be the master-agent base URL.

#### Scenario: Authenticated chat request
- **WHEN** `BackendClient.forward_message` sends a request to master-agent
- **THEN** the request SHALL include `Authorization: Bearer <id_token>` where the token audience is `agent_api_url`

#### Scenario: Authenticated voice request
- **WHEN** `BackendClient.forward_voice` sends a request to master-agent
- **THEN** the request SHALL include `Authorization: Bearer <id_token>`

#### Scenario: Authenticated image request
- **WHEN** `BackendClient.forward_image` sends a request to master-agent
- **THEN** the request SHALL include `Authorization: Bearer <id_token>`

#### Scenario: Authenticated document request
- **WHEN** `BackendClient.forward_document` sends a request to master-agent
- **THEN** the request SHALL include `Authorization: Bearer <id_token>`

### Requirement: Token fetch errors are non-fatal
The system SHALL NOT raise an exception if the identity token cannot be fetched (e.g., in local development without a metadata server). In that case the request SHALL proceed without an `Authorization` header and a warning SHALL be logged.

#### Scenario: No metadata server available
- **WHEN** `google.oauth2.id_token.fetch_id_token` raises an exception (no GCP metadata)
- **THEN** the system SHALL log a warning and send the request without an `Authorization` header
- **AND** the system SHALL NOT raise an exception or block the request

### Requirement: Token audience is the base agent URL
The system SHALL use the `agent_api_url` (stripped of trailing slash, no path) as the token audience.

#### Scenario: Correct audience derivation
- **WHEN** `agent_api_url` is `https://master-agent-3qblthn7ba-ez.a.run.app`
- **THEN** the token audience SHALL be `https://master-agent-3qblthn7ba-ez.a.run.app`
