## Requirements

### Requirement: Automatic build on push to main

The system SHALL automatically trigger a Cloud Build pipeline when code is pushed to the `main` branch.

#### Scenario: Push to main triggers build
- **WHEN** developer pushes commit to `main` branch
- **THEN** Cloud Build SHALL start a new build automatically

#### Scenario: Push to non-main branch does not trigger
- **WHEN** developer pushes commit to a feature branch (not `main`)
- **THEN** Cloud Build SHALL NOT start a build

### Requirement: Docker image build

The pipeline SHALL build a Docker image from the Dockerfile in the repository root.

#### Scenario: Successful image build
- **WHEN** Cloud Build pipeline starts
- **THEN** the system SHALL build Docker image using `Dockerfile`
- **AND** tag the image as `gcr.io/${PROJECT_ID}/telegram-bot:latest`
- **AND** tag the image as `gcr.io/${PROJECT_ID}/telegram-bot:${SHORT_SHA}`

### Requirement: Push image to Container Registry

The pipeline SHALL push the built image to Google Container Registry.

#### Scenario: Image pushed to registry
- **WHEN** Docker image build completes successfully
- **THEN** the system SHALL push the image to `gcr.io/${PROJECT_ID}/telegram-bot`

### Requirement: Deploy to Cloud Run

The pipeline SHALL deploy the built image to Cloud Run.

#### Scenario: Successful deployment
- **WHEN** image is pushed to registry
- **THEN** the system SHALL deploy to Cloud Run service `telegram-bot` in region `europe-west4`
- **AND** set environment variable `AGENT_API_URL` from substitution variable
- **AND** mount secret `TELEGRAM_BOT_TOKEN` from Secret Manager

#### Scenario: Deployment with allow-unauthenticated
- **WHEN** deploying to Cloud Run
- **THEN** the service SHALL be configured with `--allow-unauthenticated` for Telegram webhook access

### Requirement: Automatic webhook setup

The pipeline SHALL configure the Telegram webhook after successful deployment.

#### Scenario: Webhook configured after deploy
- **WHEN** Cloud Run deployment completes
- **THEN** the system SHALL retrieve bot token from Secret Manager
- **AND** derive webhook secret as `sha256(bot_token)[:32]`
- **AND** call Telegram `setWebhook` API with service URL + `/telegram/webhook`
- **AND** include `secret_token` in the webhook configuration

#### Scenario: Webhook setup failure logged
- **WHEN** webhook setup fails
- **THEN** the build SHALL log a warning but NOT fail the entire pipeline

### Requirement: cloudbuild.yaml configuration file

The pipeline SHALL be defined in `cloudbuild.yaml` at the repository root.

#### Scenario: Configuration file location
- **WHEN** Cloud Build trigger is configured
- **THEN** it SHALL use `cloudbuild.yaml` from repository root

### Requirement: Substitution variables

The pipeline SHALL support configuration via Cloud Build substitution variables.

#### Scenario: Required substitutions
- **WHEN** pipeline runs
- **THEN** the following substitutions SHALL be available:
  - `_REGION` (default: `europe-west4`)
  - `_SERVICE_NAME` (default: `telegram-bot`)
  - `_AGENT_API_URL` (no default, must be configured in trigger)

### Requirement: IAM permissions

Cloud Build service account SHALL have permissions to deploy to Cloud Run.

#### Scenario: Required IAM roles
- **WHEN** pipeline runs
- **THEN** Cloud Build service account SHALL have:
  - `roles/run.admin`
  - `roles/secretmanager.secretAccessor`
  - `roles/iam.serviceAccountUser`
