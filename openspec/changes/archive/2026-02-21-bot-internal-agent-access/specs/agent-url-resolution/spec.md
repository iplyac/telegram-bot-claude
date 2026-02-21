## MODIFIED Requirements

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
