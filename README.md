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

## Sign-up page and invite code

Friends sign up at the `SiteUrl` output of the `VoloSignup` stack, with the invite code in the link: `https://<SiteUrl>/?invite=<code>`.

The code is an SSM SecureString, created once by hand because CloudFormation cannot create SecureStrings:

```
aws ssm put-parameter --profile personal \
  --name /volo-notifier/invite-code --type SecureString \
  --value "$(python3 -c 'import secrets; print(secrets.token_urlsafe(8))')"
```

Read it back to build the link:

```
aws ssm get-parameter --profile personal --name /volo-notifier/invite-code --with-decryption --query Parameter.Value --output text
```

To revoke old links, run the `put-parameter` command again with `--overwrite`. Running Lambda containers keep the old code cached until they recycle, which can take minutes to hours.

To see or remove subscribers: AWS console, SNS, Topics, `VoloPoller-DropinsTopic...`, Subscriptions tab. To change the sports list, edit `config/sports.json` and deploy.
