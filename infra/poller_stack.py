from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_sns as sns
from constructs import Construct


class PollerStack(Stack):
    """Hourly poller: schedule, Lambda, seen-drop-ins table, SNS topics, alarm.

    The Lambda, schedule, and alarm come once the Volo query is captured.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # One row per drop-in we have already notified about. DynamoDB deletes
        # rows on its own once expires_at (epoch seconds) is in the past.
        self.seen_table = dynamodb.Table(
            self,
            "SeenDropins",
            partition_key=dynamodb.Attribute(name="dropin_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            # Only dedup state lives here, so it is safe to delete with the stack.
            removal_policy=RemovalPolicy.DESTROY,
        )

        # New drop-ins. Email now, the web push sender later.
        self.dropins_topic = sns.Topic(self, "DropinsTopic", display_name="Volo drop-ins")

        # "Poller broken" alerts from the CloudWatch alarm.
        self.ops_topic = sns.Topic(self, "OpsTopic", display_name="Volo notifier ops")
