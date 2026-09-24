import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from infra.poller_stack import PollerStack


def synth(**kwargs) -> Template:
    app = cdk.App()
    stack = PollerStack(
        app, "TestPoller", env=cdk.Environment(account="123456789012", region="us-east-1"), **kwargs
    )
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


def test_poller_lambda_gets_table_and_topic_from_env():
    synth().has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.12",
            "Handler": "handler.handler",
            "Environment": {"Variables": {"TABLE_NAME": Match.any_value(), "TOPIC_ARN": Match.any_value()}},
        },
    )


def test_schedule_is_off_unless_enabled():
    synth().has_resource_properties("AWS::Events::Rule", {"State": "DISABLED"})
    synth(schedule_enabled=True).has_resource_properties("AWS::Events::Rule", {"State": "ENABLED"})


def test_alarm_fires_on_any_error():
    synth().has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"MetricName": "Errors", "Threshold": 1, "ComparisonOperator": "GreaterThanOrEqualToThreshold"},
    )


def test_email_subscribes_to_both_topics():
    synth(notify_email="me@example.com").resource_count_is("AWS::SNS::Subscription", 2)
    synth().resource_count_is("AWS::SNS::Subscription", 0)
