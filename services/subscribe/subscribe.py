"""Subscribe Lambda, behind a public Function URL.

Takes {email, sports, invite} from the sign-up page and subscribes the email to the
drop-ins topic with a filter policy for those sports. SNS then sends its own
confirmation email, so nobody can sign up an address they do not control.
"""

import base64
import json
import os

import boto3

from validation import InvalidRequest, parse_signup

sns = boto3.client("sns")
ssm = boto3.client("ssm")

_invite_code = None


def invite_code() -> str:
    """Read once per Lambda container, then reuse. Changing the code in SSM takes
    effect as containers recycle (minutes to hours)."""
    global _invite_code
    if _invite_code is None:
        param = ssm.get_parameter(Name=os.environ["INVITE_CODE_PARAM"], WithDecryption=True)
        _invite_code = param["Parameter"]["Value"]
    return _invite_code


def handler(event, context):
    if event.get("requestContext", {}).get("http", {}).get("method") != "POST":
        return respond(405, "Use POST.")

    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()

    allowed = set(os.environ["ALLOWED_SPORTS"].split(","))
    try:
        email, sports = parse_signup(body, invite_code(), allowed)
    except InvalidRequest as e:
        return respond(400, str(e))

    status = subscribe(os.environ["TOPIC_ARN"], email, sports)
    print(json.dumps({"status": status, "sports": sports}))  # no email in logs
    messages = {
        "created": "Check your inbox and click the confirmation link from AWS.",
        "updated": "You were already subscribed. Your sports are updated.",
        "pending": "Check your inbox. You still need to click the confirmation link from AWS.",
    }
    return respond(200, messages[status], status=status)


def subscribe(topic_arn: str, email: str, sports: list[str]) -> str:
    """Create or update the subscription. Returns created, updated, or pending."""
    filter_policy = json.dumps({"sport": sports})

    existing = find_subscription(topic_arn, email)
    if existing is None:
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint=email,
            Attributes={"FilterPolicy": filter_policy},
        )
        return "created"
    if existing == "PendingConfirmation":
        # SNS does not allow changing a subscription until it is confirmed.
        return "pending"
    sns.set_subscription_attributes(
        SubscriptionArn=existing, AttributeName="FilterPolicy", AttributeValue=filter_policy
    )
    return "updated"


def find_subscription(topic_arn: str, email: str) -> str | None:
    """Subscription ARN for this email, "PendingConfirmation", or None.

    Scans the topic's subscribers. Fine for a list of friends; a big list would
    want its own index.
    """
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=topic_arn):
        for sub in page["Subscriptions"]:
            if sub["Protocol"] == "email" and sub["Endpoint"].lower() == email.lower():
                return sub["SubscriptionArn"]
    return None


def respond(status_code: int, message: str, **extra) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message, **extra}),
    }
