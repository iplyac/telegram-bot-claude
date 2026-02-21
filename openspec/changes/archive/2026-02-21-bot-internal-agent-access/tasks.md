## 1. Dependency

- [x] 1.1 Verify `google-auth` is in `requirements.txt`; add `google-auth>=2.0.0` if absent

## 2. BackendClient: identity token authentication

- [x] 2.1 Add `_get_auth_headers(self) -> dict` private method to `BackendClient` that calls `google.oauth2.id_token.fetch_id_token(request, audience)` where audience is `self.agent_api_url.rstrip('/')`
- [x] 2.2 Wrap the `fetch_id_token` call in try/except; on exception log a warning and return `{}`
- [x] 2.3 Pass `headers=await self._get_auth_headers()` (or sync equivalent) into every `self._client.post(...)` call inside `_post_with_retry`

## 3. deploy-bot.sh: VPC egress, default URL, IAM binding

- [x] 3.1 Add `AGENT_API_URL` compile-time default: `AGENT_API_URL="${AGENT_API_URL:-https://master-agent-3qblthn7ba-ez.a.run.app}"`
- [x] 3.2 Add `--network=default --subnet=default --vpc-egress=all-traffic` to both `gcloud run deploy` invocations in the script
- [x] 3.3 Add post-deploy IAM binding step: `gcloud run services add-iam-policy-binding master-agent --member="serviceAccount:$(gcloud run services describe $SERVICE_NAME ... --format='value(spec.template.spec.serviceAccountName)')" --role=roles/run.invoker`

## 4. Tests

- [x] 4.1 Add unit test: `_get_auth_headers` returns `{"Authorization": "Bearer <token>"}` when `fetch_id_token` succeeds (mock `fetch_id_token`)
- [x] 4.2 Add unit test: `_get_auth_headers` returns `{}` and logs warning when `fetch_id_token` raises
- [x] 4.3 Add unit test: `_post_with_retry` passes auth headers to `httpx` client (verify header forwarded in the POST call)
- [x] 4.4 Verify existing tests still pass (no regressions)
