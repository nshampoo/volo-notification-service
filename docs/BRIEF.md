# Volo Drop-in Notifier: Project Brief

## Goal

Get a push notification on my iPhone when a new flag football drop-in opens up on Volo Sports in NYC, so I can grab it and play more.

This is also AWS practice. I've used AWS professionally but this is my first personal account. Favor clear, idiomatic AWS CDK over clever shortcuts, and explain AWS concepts as we go when they're new.

## Background

- Volo Sports runs adult rec leagues in NYC. A "drop-in" is an open sub spot: a team captain posts one when their team is short for a game.
- Drop-ins show up on Volo's website ("Find a drop-in") and in their app.
- Volo has no public API. Their backend is GraphQL. The plan is to capture the drop-in list request from the website in Chrome DevTools, then replay it from a Lambda.
- Drop-ins are often posted close to game time, so latency matters somewhat. Hourly polling to start.

## What we're building

```
EventBridge (hourly) -> Poller Lambda -> DynamoDB (seen drop-in IDs, TTL)
                                      -> SNS topic -> Sender Lambda -> Web Push -> iPhone
CloudWatch alarm on poller errors -> ops SNS topic -> email
```

### 1. Poller
- Runs hourly on an EventBridge schedule.
- Makes one GraphQL request to Volo per run (be polite, no hammering).
- Filters results: flag football, NYC, at least one spot open, game in the future. Later: specific nights or locations.
- Dedups: records each drop-in ID in DynamoDB and only notifies the first time it sees one. Rows expire via TTL after the game date.
- Publishes each new drop-in to an SNS topic with a title, body (day, time, location, spots left), and a link to the drop-in.
- If the Volo request fails or the response shape changes, alert me ("poller broken") instead of failing silently.

### 2. Delivery: home-screen web app with web push
- No App Store app. A small web app hosted on S3 + CloudFront (HTTPS) that I add to my iPhone Home Screen. iOS 16.4+ supports web push for Home Screen web apps.
- Page has an "Enable notifications" button (iOS requires the permission prompt to come from a user tap), a web app manifest, and a service worker that shows the notification and opens the drop-in link on tap.
- A subscribe endpoint (Lambda Function URL or API Gateway) saves my push subscription to DynamoDB.
- A sender Lambda subscribes to the SNS topic and sends the push using VAPID keys (e.g. `pywebpush`). VAPID keys live in SSM Parameter Store.
- SNS stays in the middle so delivery can change later without touching the poller. Email can subscribe to the same topic as a backup channel.

### 3. Ops
- CloudWatch alarm on poller Lambda errors, notifying an ops SNS topic subscribed to my email.

## Tech decisions

- **AWS CDK in Python**, Lambdas in Python 3.12. One repo for infrastructure and application code, deployed with `cdk deploy`.
- Two stacks: a poller stack (schedule, Lambda, DynamoDB, SNS, alarm) and a push stack (S3, CloudFront, subscribe and sender Lambdas, subscriptions table).
- Lambdas with third-party dependencies are built with `PythonFunction` (bundles in Docker so compiled deps match Lambda's Linux). Keep the poller dependency-free if possible (stdlib `urllib`).
- Keep pure logic (filtering, message formatting, response parsing) in separate modules with pytest tests.

Suggested layout:
```
volo-notifier/
  infra/        CDK app and stacks
  services/     poller/, subscribe/, sender/ Lambdas
  web/          home-screen web app (HTML, manifest, service worker)
  tests/
  local/        gitignored: captured Volo request and sample response
```

## Hard constraints

- **The AWS account is on the Free plan.** Do not create or join an AWS Organization, and do not enable IAM Identity Center. Either one permanently upgrades the account to a paid plan and ends the free credits.
- Auth is an IAM user with `aws login --profile personal` (CLI 2.32.0+, temporary credentials). **No long-lived access keys.** I run `aws login` myself since it opens a browser.
- Always use `--profile personal`. I also have work AWS profiles on this machine; never touch them.
- Region: `us-east-1`.
- Stay in always-free territory: Lambda, DynamoDB on-demand, SNS, small S3/CloudFront. A $5/month budget alert is set up.
- **Secrets never go in git.** The captured Volo cURL request and sample response live in `local/` (gitignored). Any Volo auth token goes in SSM Parameter Store as a SecureString.
- Respect Volo: one request per run, hourly to start. Don't redistribute their data.

## Build order

1. **Setup check.** Confirm `aws sts get-caller-identity --profile personal` shows my IAM user (not root). Run `cdk bootstrap` if needed. Scaffold the repo, `.gitignore`, and README.
2. **Capture the query.** I'll paste the Volo GraphQL request (as cURL) and a sample response into `local/`. Figure out whether it needs auth and how the token expires.
3. **Poller.** Implement fetch, parse, filter, and dedup with tests against the sample response. Deploy with an email subscription on the SNS topic first, invoke manually, then enable the hourly schedule.
4. **Web push.** Build the home-screen web app, subscribe endpoint, and sender Lambda. Test on my iPhone.
5. **Tune.** Consider polling every 15 minutes on weekday evenings. Adjust filters (nights, locations) once I see real data.

## Done looks like

- A new flag football drop-in in NYC produces one push notification on my iPhone within about an hour, and tapping it opens the drop-in.
- The same drop-in never notifies twice.
- If the poller breaks, I get an email.
- The whole thing deploys with one `cdk deploy` and costs roughly nothing.

## Account setup status (not code)

- Done: account on the Free plan, region us-east-1, monthly budget with email alerts.
- Still to do: MFA on root and on the IAM user. Remind me before anything runs on a schedule.

## Style

Docs, comments, and commit messages: direct and plain, no em-dashes.

## Plan changes (2026-09-23)

Decided after step 3, replacing step 4 above:

- **Email first, for friends too.** A sign-up page where anyone with the link enters their email and picks sports. The subscribe endpoint calls SNS `subscribe` with protocol `email`, so SNS handles double opt-in and unsubscribe links.
- **Sports via SNS filter policies.** The poller fetches every sport in its one request and tags each message with a `sport` attribute (Volo's slug, e.g. `flag-football`). Each subscription's filter policy picks sports. The owner's subscription is `flag-football` only.
- **Invite code.** The sign-up page and endpoint require a code in the shared link, to keep it among friends (Volo's data) and stop form abuse. The code lives in SSM Parameter Store, not git.
- **Admin is the AWS console.** SNS topic Subscriptions tab shows each email, status, and filter policy, with delete and edit. No custom admin script or page.
- **Web push is parked** for later. Filters for nights and neighborhoods are also later.
- **MFA:** owner chose to run the schedule before enabling MFA. Still recommended.

Revised build order:
1. Hourly schedule on. Done.
2. Poller publishes all sports with a `sport` tag. Done.
3. Sign-up stack: S3 + CloudFront page with sport checkboxes, subscribe Lambda behind a Function URL, invite code in SSM.
4. Later: web push, more filters.
