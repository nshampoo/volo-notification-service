"""Dedup and publish behavior, with fake DynamoDB and SNS clients."""

import json

import pytest
from botocore.exceptions import ClientError

import handler
from parse import parse_response
from test_poller_logic import FIXTURE


class FakeDynamo:
    def __init__(self):
        self.rows = {}

    def put_item(self, TableName, Item, ConditionExpression):
        key = Item["dropin_id"]["S"]
        if key in self.rows:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.rows[key] = Item

    def delete_item(self, TableName, Key):
        self.rows.pop(Key["dropin_id"]["S"], None)


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


def test_failed_publish_forgets_the_dropin_so_next_run_retries(monkeypatch, dropin):
    dynamo = FakeDynamo()
    monkeypatch.setattr(handler, "dynamodb", dynamo)
    monkeypatch.setattr(handler, "sns", FakeSns(fail=True))

    with pytest.raises(RuntimeError):
        handler.notify_once(dropin, "table", "topic")
    assert dynamo.rows == {}
