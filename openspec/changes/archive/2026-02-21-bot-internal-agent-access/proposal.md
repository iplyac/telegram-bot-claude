## Why

master-agent was moved to `--ingress=internal --no-allow-unauthenticated` for security. The Telegram bot must now reach it via VPC (Direct VPC Egress with `all-traffic`) and authenticate every HTTP request with a Google Cloud identity token — neither of which the bot currently does.

## What Changes

- **BREAKING**: `BackendClient` adds `Authorization: Bearer <id_token>` header to every request to master-agent; plain unauthenticated calls will no longer work
- `deploy-bot.sh` gains `--vpc-egress=all-traffic` flag (currently `private-ranges-only`)
- `deploy-bot.sh` hardcodes a default for `AGENT_API_URL` so it is never accidentally missing
- `deploy-bot.sh` adds a post-deploy `gcloud run services add-iam-policy-binding` step granting the bot's SA `roles/run.invoker` on master-agent (idempotent)
- New Python dependency: `google-auth` (for `google.oauth2.id_token.fetch_id_token`)

## Capabilities

### New Capabilities
- `agent-auth`: `BackendClient` fetches a Google Cloud ID token scoped to the master-agent URL and attaches it as a Bearer token on every outbound request. Tokens are cached until expiry.

### Modified Capabilities
- `agent-url-resolution`: the requirement that `AGENT_API_URL` must be explicitly provided is relaxed — a compile-time default is now baked into `deploy-bot.sh`, making the env var optional at deploy time.

## Impact

- **Files modified**: `tgbot/services/backend_client.py`, `deploy-bot.sh`, `requirements.txt`
- **New dependency**: `google-auth` (already a transitive dep of `google-cloud-*`, likely already present)
- **Infrastructure**: `--vpc-egress=all-traffic` on Cloud Run telegram-bot; IAM binding bot-SA → master-agent `roles/run.invoker`
- **No handler changes**: all five handlers (text, voice, image, document, commands) continue to use `BackendClient` unchanged
