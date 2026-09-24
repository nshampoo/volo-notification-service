from pathlib import Path

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct

POLLER_CODE = Path(__file__).parent.parent / "services" / "poller"


class PollerStack(Stack):
    """Hourly poller: schedule, Lambda, seen-drop-ins table, SNS topics, alarm."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        notify_email: str | None = None,
        schedule_enabled: bool = False,
        **kwargs,
    ) -> None:
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

        if notify_email:
            # The poller tags every message with its sport. The filter policy means
            # this subscription only receives flag football.
            self.dropins_topic.add_subscription(
                subs.EmailSubscription(
                    notify_email,
                    filter_policy={"sport": sns.SubscriptionFilter.string_filter(allowlist=["flag-football"])},
                )
            )
            self.ops_topic.add_subscription(subs.EmailSubscription(notify_email))

        # Stdlib only (boto3 ships with the Lambda runtime), so a plain zip of the
        # folder works and no Docker bundling is needed.
        self.poller = lambda_.Function(
            self,
            "Poller",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset(str(POLLER_CODE), exclude=["__pycache__"]),
            handler="handler.handler",
            # A first run can publish ~80 drop-ins across all sports.
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "TABLE_NAME": self.seen_table.table_name,
                "TOPIC_ARN": self.dropins_topic.topic_arn,
            },
            log_group=logs.LogGroup(
                self,
                "PollerLogs",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )
        # Grants add least-privilege IAM statements to the Lambda's execution role.
        self.seen_table.grant_read_write_data(self.poller)
        self.dropins_topic.grant_publish(self.poller)

        # Any failed run (Volo down, response shape changed, bug) emails the ops topic.
        errors_alarm = cloudwatch.Alarm(
            self,
            "PollerErrors",
            alarm_description="Volo poller failed. Check the Poller Lambda logs.",
            metric=self.poller.metric_errors(period=Duration.hours(1)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        errors_alarm.add_alarm_action(cw_actions.SnsAction(self.ops_topic))
        errors_alarm.add_ok_action(cw_actions.SnsAction(self.ops_topic))

        events.Rule(
            self,
            "HourlySchedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.LambdaFunction(self.poller)],
            enabled=schedule_enabled,
        )
