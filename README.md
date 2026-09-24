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

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
cdk diff      # cdk.json pins the personal profile
cdk deploy
```

## Manual test

Invoke the poller for one sport that has open drop-ins, capped to one notification:

```
aws lambda invoke --profile personal --cli-binary-format raw-in-base64-out \
  --function-name <Poller function name> \
  --payload '{"sport":"soccer","max_publish":1}' out.json
```

The email only arrives if your subscription's filter policy includes that sport. A second identical invoke should report `"published": 0` (dedup).
