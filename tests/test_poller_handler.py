"""Dedup and publish behavior, with fake DynamoDB and SNS clients."""

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

import handler
from parse import parse_response
from test_poller_logic import BEFORE_GAMES, FIXTURE


class FakeDynamo:
    def __init__(self):
        self.rows = {}
        self.counts = {}

    def put_item(self, TableName, Item, ConditionExpression):
        key = Item["dropin_id"]["S"]
        if key in self.rows:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.rows[key] = Item

    def delete_item(self, TableName, Key):
        self.rows.pop(Key["dropin_id"]["S"], None)

    def update_item(self, TableName, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues):
        # Enough of DynamoDB's ADD to check the daily counts.
        day = self.counts.setdefault(Key["day"]["S"], {"total": 0, "football": 0})
        day["total"] += int(ExpressionAttributeValues[":one"]["N"])
        day["football"] += int(ExpressionAttributeValues[":football"]["N"])


class FakeSns:
    def __init__(self, fail=False):
        self.published = []
        self.fail = fail

    def publish(self, **kwargs):
        if self.fail:
            raise RuntimeError("SNS down")
        self.published.append(kwargs)


@pytest.fixture
def dropin():
    return parse_response(FIXTURE)[0]


def test_notifies_once_per_dropin(monkeypatch, dropin):
    dynamo, sns = FakeDynamo(), FakeSns()
    monkeypatch.setattr(handler, "dynamodb", dynamo)
    monkeypatch.setattr(handler, "sns", sns)

    assert handler.notify_once(dropin, "table", "topic") is True
    assert handler.notify_once(dropin, "table", "topic") is False
    assert len(sns.published) == 1

    row = dynamo.rows["game-flag-open"]
    assert int(row["expires_at"]["N"]) > dropin.start.timestamp()


def test_publish_sends_json_by_default_and_text_to_email(monkeypatch, dropin):
    sns = FakeSns()
    monkeypatch.setattr(handler, "dynamodb", FakeDynamo())
    monkeypatch.setattr(handler, "sns", sns)

    handler.notify_once(dropin, "table", "topic")
    sent = sns.published[0]
    assert sent["MessageStructure"] == "json"
    message = json.loads(sent["Message"])
    assert json.loads(message["default"])["url"] == dropin.url
    assert dropin.url in message["email"]
    assert sent["MessageAttributes"]["sport"]["StringValue"] == "flag-football"


def test_failed_publish_forgets_the_dropin_so_next_run_retries(monkeypatch, dropin):
    dynamo = FakeDynamo()
    monkeypatch.setattr(handler, "dynamodb", dynamo)
    monkeypatch.setattr(handler, "sns", FakeSns(fail=True))

    with pytest.raises(RuntimeError):
        handler.notify_once(dropin, "table", "topic")
    assert dynamo.rows == {}


@pytest.fixture
def run(monkeypatch):
    """Call handler.handler against the fixture with fake AWS clients."""
    sns, dynamo = FakeSns(), FakeDynamo()
    monkeypatch.setattr(handler, "dynamodb", dynamo)
    monkeypatch.setattr(handler, "sns", sns)
    monkeypatch.setenv("TABLE_NAME", "table")
    monkeypatch.setenv("TOPIC_ARN", "topic")
    monkeypatch.setenv("STATS_TABLE_NAME", "stats")
    monkeypatch.setattr(handler.volo, "fetch", lambda body: FIXTURE)
    monkeypatch.setattr(handler, "datetime", type("D", (), {"now": staticmethod(lambda tz: BEFORE_GAMES)}))
    go = lambda event: (handler.handler(event, None), sns.published)  # noqa: E731
    go.dynamo = dynamo
    return go


def test_scheduled_run_publishes_and_counts_every_open_sport(run):
    result, published = run({"source": "aws.events"})
    assert result == {"fetched": 3, "wanted": 2, "published": 2}
    assert [p["MessageAttributes"]["sport"]["StringValue"] for p in published] == ["flag-football", "soccer"]
    # Both new drop-ins land in one day's tally; one of them was flag football.
    assert [day for day in run.dynamo.counts.values()] == [{"total": 2, "football": 1}]


def test_manual_invoke_can_limit_to_one_sport_and_cap_publishes(run):
    result, published = run({"sport": "soccer", "max_publish": 1})
    assert result == {"fetched": 3, "wanted": 1, "published": 1}
    assert published[0]["Subject"].startswith("Soccer drop-in")


def test_counts_new_dropins_by_new_york_day(monkeypatch, dropin):
    dynamo = FakeDynamo()
    monkeypatch.setattr(handler, "dynamodb", dynamo)
    other = replace(dropin, game_id="game-soccer", sport_slug="soccer")

    # 01:30 UTC on Oct 3 is still Oct 2 in New York.
    spotted = datetime(2026, 10, 3, 1, 30, tzinfo=timezone.utc)
    handler.count_dropin(dropin, "stats", spotted)
    handler.count_dropin(other, "stats", spotted)

    assert dynamo.counts == {"2026-10-02": {"total": 2, "football": 1}}


def test_a_failed_count_never_breaks_the_alert(monkeypatch, dropin):
    class BrokenStats(FakeDynamo):
        def update_item(self, **kwargs):
            raise RuntimeError("DynamoDB down")

    monkeypatch.setattr(handler, "dynamodb", BrokenStats())
    handler.count_dropin(dropin, "stats", datetime(2026, 10, 2, 12, tzinfo=timezone.utc))
