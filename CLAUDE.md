# Notes for Claude

Read `docs/BRIEF.md` first. It is the source of truth for goals, architecture, and hard constraints.

## Working style

- This is a learning project. Explain new AWS concepts as they come up, and explain each step before running it.
- The user wants to be involved at every step. Ask before creating AWS resources or committing.
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
- [ ] `cdk bootstrap` for us-east-1.
- [ ] MFA on root and on `nick`. Remind the user before anything runs on a schedule.
- [ ] Docker installed (needed for `PythonFunction` in step 4).
- [ ] Step 2: capture the Volo query.
