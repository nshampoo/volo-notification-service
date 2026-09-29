# Setting up a new machine

Everything that runs lives in AWS, so moving laptops never interrupts the poller or the sign-up site. The laptop only needs tools, a login, and a clone of this repo.

## 1. Tools

```
# Homebrew, if not installed: https://brew.sh
brew install git node awscli python@3.12
npm install -g aws-cdk
aws --version    # needs 2.32.0 or newer for `aws login`
cdk --version
```

Docker is only needed for web push later. Skip it for now.

## 2. GitHub access

Make a new SSH key for this machine instead of copying the old one. Each laptop gets its own key, and an old laptop's key can be revoked on its own.

```
ssh-keygen -t ed25519 -C "ShampooShoulders@gmail.com"
pbcopy < ~/.ssh/id_ed25519.pub
```

Paste it at https://github.com/settings/ssh/new, then check: `ssh -T git@github.com` should say "Hi nshampoo!".

```
git config --global user.name "Nick Shampoe"
git config --global user.email "ShampooShoulders@gmail.com"
```

## 3. Clone the repo

Clone into a folder outside iCloud Drive, e.g. `~/Code`. iCloud "Desktop & Documents" sync does not get along with `.git` and `.venv` folders (half-synced files, conflict copies).

```
mkdir -p ~/Code && cd ~/Code
git clone git@github.com:nshampoo/volo-notification-service.git
cd volo-notification-service
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## 4. AWS login

```
aws login --profile personal
```

- Region prompt: `us-east-1`.
- In the browser, sign in as the **IAM user `nick`**, not root.
- "Configure AWS skills and the AWS MCP server?" prompt: answer `n`.

No access keys to copy. Credentials are temporary and made fresh by `aws login`.

## 5. Check it all works

```
aws sts get-caller-identity --profile personal   # Arn must end in :user/nick
cdk diff --all                                   # expect no differences
```

`cdk diff` showing no differences means the new clone matches what is deployed.

## 6. Things not in git (optional)

- `local/`: captured Volo samples. Only reference data. Copy it over (AirDrop) if wanted, or skip it.
- The invite code is in SSM, not on the laptop. Read it with the command in the README.

## 7. Retire the old laptop

- `aws logout --profile personal`
- Delete its SSH key at https://github.com/settings/keys
