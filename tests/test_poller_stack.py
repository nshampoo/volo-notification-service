import aws_cdk as cdk
from aws_cdk.assertions import Template

from infra.poller_stack import PollerStack


def synth() -> Template:
    app = cdk.App()
    stack = PollerStack(app, "TestPoller", env=cdk.Environment(account="123456789012", region="us-east-1"))
    return Template.from_stack(stack)


def test_seen_table_is_on_demand_with_ttl():
    synth().has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "BillingMode": "PAY_PER_REQUEST",
            "KeySchema": [{"AttributeName": "dropin_id", "KeyType": "HASH"}],
            "TimeToLiveSpecification": {"AttributeName": "expires_at", "Enabled": True},
        },
    )


def test_has_dropins_and_ops_topics():
    synth().resource_count_is("AWS::SNS::Topic", 2)
