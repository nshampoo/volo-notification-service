# Volo Drop-in Notifier

Sends a push notification to my iPhone when a new flag football drop-in opens on Volo Sports in NYC.

An hourly Lambda checks Volo for drop-ins, skips ones it has already seen, and publishes new ones to SNS. A second Lambda turns those into web push notifications for a home-screen web app. Everything is AWS CDK in Python.

See [docs/BRIEF.md](docs/BRIEF.md) for the full plan and constraints.

## Prerequisites

- AWS CLI 2.32.0 or newer, logged in with `aws login --profile personal`
- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.12 or newer
- Docker (for bundling Lambdas that have dependencies)

## Private files

`local/` is gitignored. Captured Volo requests and sample responses go there and never get committed.
