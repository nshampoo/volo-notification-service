# Notes for Claude

Read `docs/BRIEF.md` first. It is the source of truth for goals, architecture, and hard constraints.

## Working style

- This is a learning project. Explain new AWS concepts briefly as they come up.
- Keep the pace up: batch routine steps and keep explanations short. Commit at logical checkpoints and push to `origin main`.
- Ask before `cdk deploy` or anything else that creates or changes AWS resources.
- Docs, comments, and commit messages: direct and plain, no em-dashes.
- No Claude attribution in commits or PRs (no Co-Authored-By line, no "Generated with" footer).

## Hard constraints (short version, details in the brief)

- Never create or join an AWS Organization. Never enable IAM Identity Center. Either one ends the Free plan.
- Always pass `--profile personal`. Never use any other AWS profile on this machine.
- Region `us-east-1`.
- No long-lived access keys. The user runs `aws login --profile personal` themselves (it opens a browser).
- Secrets and captured Volo requests/responses stay in `local/` (gitignored) or SSM Parameter Store. Never in git.
- One Volo request per poller run.

## Progress

- [x] AWS CLI and CDK CLI installed. Logged in as IAM user `nick` (verified not root).
- [x] Repo initialized with brief, `.gitignore`, README.
- [x] `cdk bootstrap` for us-east-1.
- [x] CDK Python scaffold: `infra/` (app, `VoloPoller` stack with table and topics, not deployed yet), `tests/`, `.venv`.
- [x] Pushed to github.com/nshampoo/volo-notification-service (private).
- [ ] MFA on root and on `nick`. Remind the user before anything runs on a schedule.
- [ ] Docker installed (needed for `PythonFunction` in step 4).
- [x] Step 2: Volo query captured. See "Volo API" below.

## Volo API

- `POST https://www.volosports.com/hapi/v1/graphql`, plain JSON, no auth or cookies needed (verified 2026-09-23).
- Backend is Hasura, so filters use `_eq` / `_gte` / `_is_null` bool_exp syntax, and unknown fields return an error.
- Our trimmed query: `services/poller/dropins.graphql`, table `discover_daily`, one row per game with open drop-in spots.
- Volo NYC organization ID: `ff4d79f6-bba5-45dc-8532-46b8cf05f6e2`. Flag Football sport ID: `6a4c2578-be2b-41cf-8b8a-f8c3ede1cfea`.
- Samples in `local/`: `sample_response.json` (flag football, 0 rows at capture time), `sample_response_all.json` (all sports, 78 rows).
