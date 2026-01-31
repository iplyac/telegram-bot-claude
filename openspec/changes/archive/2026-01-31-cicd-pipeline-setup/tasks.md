## 1. Create cloudbuild.yaml

- [x] 1.1 Create `cloudbuild.yaml` with build step (docker build)
- [x] 1.2 Add push step (docker push to gcr.io)
- [x] 1.3 Add deploy step (gcloud run deploy)
- [x] 1.4 Add webhook setup step (curl setWebhook)
- [x] 1.5 Configure substitution variables (_REGION, _SERVICE_NAME, _AGENT_API_URL)

## 2. Configure IAM permissions

- [x] 2.1 Grant Cloud Build service account `roles/run.admin`
- [x] 2.2 Grant Cloud Build service account `roles/secretmanager.secretAccessor`
- [x] 2.3 Grant Cloud Build service account `roles/iam.serviceAccountUser`

## 3. Create Cloud Build trigger

- [x] 3.1 Connect GitHub repository to Cloud Build
- [x] 3.2 Create trigger for push to main branch
- [x] 3.3 Configure substitution variables in trigger (_AGENT_API_URL)

## 4. Test pipeline

- [x] 4.1 Push test commit to main
- [x] 4.2 Verify build completes successfully
- [x] 4.3 Verify Cloud Run deployment
- [x] 4.4 Verify webhook is configured
- [x] 4.5 Send test message to bot
