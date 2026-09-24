"""Poller Lambda: fetch drop-ins, skip ones already seen, publish new ones to SNS."""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

import volo
from filters import is_open
from message import format_email, format_message
from parse import parse_response

# Keep dedup rows a day past the game so a late re-listing still counts as seen.
TTL_AFTER_GAME = timedelta(days=1)

dynamodb = boto3.client("dynamodb")
sns = boto3.client("sns")


def handler(event, context):
    """Scheduled runs send an EventBridge event, which has neither override.

    For a manual test, invoke with {"sport": "soccer", "max_publish": 1} to publish
    only that sport, without flooding anyone's inbox.
    """
    event = event or {}
    only_sport = event.get("sport")
    max_publish = event.get("max_publish")

    now = datetime.now(timezone.utc)
    dropins = parse_response(volo.fetch(volo.build_request_body(now)))
    if len(dropins) >= volo.LIMIT:
        print(f"WARNING: hit the {volo.LIMIT} row limit, some drop-ins may be missing")
    wanted = [d for d in dropins if is_open(d, now) and (only_sport is None or d.sport_slug == only_sport)]
    if max_publish is not None:
        wanted = wanted[:max_publish]

    published = 0
    for dropin in wanted:
        if notify_once(dropin, os.environ["TABLE_NAME"], os.environ["TOPIC_ARN"]):
            published += 1

    result = {"fetched": len(dropins), "wanted": len(wanted), "published": published}
    print(json.dumps(result))
    return result


def notify_once(dropin, table_name: str, topic_arn: str) -> bool:
    """Publish a drop-in unless we already have. Returns True if published."""
    key = {"dropin_id": {"S": dropin.game_id}}
    expires_at = int((dropin.start + TTL_AFTER_GAME).timestamp())

    # Conditional put: DynamoDB only writes the row if it does not exist yet,
    # so the check and the write are one atomic step.
    try:
        dynamodb.put_item(
            TableName=table_name,
            Item={**key, "expires_at": {"N": str(expires_at)}},
            ConditionExpression="attribute_not_exists(dropin_id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise

    try:
        publish(dropin, topic_arn)
    except Exception:
        # Forget the row so the next run retries instead of silently dropping it.
        dynamodb.delete_item(TableName=table_name, Key=key)
        raise
    return True


def publish(dropin, topic_arn: str) -> None:
    msg = format_message(dropin)
    sns.publish(
        TopicArn=topic_arn,
        Subject=msg["title"][:100],
        # Subscribers' filter policies match on this, e.g. {"sport": ["flag-football"]}.
        MessageAttributes={"sport": {"DataType": "String", "StringValue": dropin.sport_slug}},
        # "json" structure lets each subscriber type get its own format:
        # email gets readable text, everything else (the sender Lambda) gets JSON.
        MessageStructure="json",
        Message=json.dumps(
            {
                "default": json.dumps(msg),
                "email": format_email(msg),
            }
        ),
    )
