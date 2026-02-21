## Context

master-agent was hardened to `--ingress=internal --no-allow-unauthenticated`. The Telegram bot is a Cloud Run service in the same project and VPC (`default` network, `europe-west4`). Its current egress is `private-ranges-only`, meaning traffic to Cloud Run public URLs (`*.run.app`) exits through the public internet — bypassing internal ingress. `BackendClient` uses plain `httpx` with no auth headers.

Two independent problems must be solved:
1. **Network**: bot must route all outbound traffic through the VPC so master-agent's `ingress=internal` accepts it
2. **Auth**: every request needs `Authorization: Bearer <id_token>` scoped to the master-agent URL

## Goals / Non-Goals

**Goals:**
- Telegram bot reaches master-agent through Direct VPC Egress (`all-traffic`)
- Every outbound HTTP call to master-agent carries a valid Google Cloud ID token
- Deploy script ensures VPC egress + IAM binding are set on every deploy
- `AGENT_API_URL` has a compile-time default so accidental omission doesn't silently break the bot

**Non-Goals:**
- Changing handler code (text, voice, image, document, commands remain untouched)
- Supporting multiple agent backends
- Rotating or caching tokens beyond what `google-auth` does natively

## Decisions

### 1. Token per-request via `google.oauth2.id_token.fetch_id_token`

`google-auth` already handles caching and automatic refresh internally. Calling `fetch_id_token(request, audience)` is cheap when the token is still valid. We call it once per HTTP request inside `_get_auth_headers()` — a private helper on `BackendClient`. No manual TTL tracking needed.

**Alternative considered:** Cache token in an instance variable with explicit expiry check. Rejected — duplicates what `google-auth` already does and adds complexity.

### 2. Audience = base master-agent URL (no path)

Google Cloud ID tokens for Cloud Run must use the service's root URL as the audience (e.g., `https://master-agent-3qblthn7ba-ez.a.run.app`). Including a path would fail token validation on the server side.

`BackendClient` already stores `agent_api_url` — we strip any trailing slash and use it directly as the audience.

### 3. `httpx.AsyncClient` gets a default `headers` dict, not per-request

Setting auth headers once on the client via `default_headers` would cache a token indefinitely. Instead we pass `headers=` per-request so `_get_auth_headers()` is called fresh each time, and `google-auth` decides whether to return the cached or refreshed token.

**Alternative:** Use `httpx.AsyncClient` with a custom `Auth` flow class. Rejected — overkill for a single header; the explicit per-request call is easier to test and reason about.

### 4. Graceful degradation in non-GCP environments

`fetch_id_token` raises when there is no metadata server (local dev, CI). `_get_auth_headers()` catches the exception, logs a warning, and returns an empty dict. The request proceeds without auth. This preserves current local-dev behaviour.

### 5. `AGENT_API_URL` default baked into `deploy-bot.sh`

The URL is stable (hash is tied to project/region). Hardcoding it in the script makes deploys idempotent. The env var override remains so it can still be changed without editing the script.

## Risks / Trade-offs

- **Token fetch latency** (~10 ms on first call, ~0 ms on cache hit) → negligible vs. agent processing time (seconds)
- **SA permissions drift** → mitigated by idempotent `add-iam-policy-binding` in deploy script
- **Local dev breaks if google-auth not installed** → already a transitive dependency; catch block prevents hard failure
- **`all-traffic` VPC egress routes ALL outbound traffic through VPC** → no direct internet egress from bot instance; Telegram API calls also go through VPC NAT. This is acceptable since Cloud NAT is configured for the default network.
