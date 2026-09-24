import os

import aws_cdk as cdk

from infra.poller_stack import PollerStack

app = cdk.App()

# The CLI fills in CDK_DEFAULT_ACCOUNT from the profile in cdk.json, so the
# account ID never needs to live in git. Region is pinned.
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region="us-east-1")

PollerStack(
    app,
    "VoloPoller",
    env=env,
    notify_email=app.node.try_get_context("notify_email"),
    schedule_enabled=app.node.try_get_context("schedule_enabled") is True,
)

app.synth()
