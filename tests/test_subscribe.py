"""Sign-up validation and the subscribe Lambda, with a fake SNS client."""

import json

import pytest

import subscribe
from validation import InvalidRequest, parse_signup

INVITE = "letmein"
ALLOWED = {"flag-football", "soccer"}


def body(**overrides):
    data = {"email": "friend@example.com", "sports": ["flag-football"], "invite": INVITE}
    data.update(overrides)
    return json.dumps(data)


def test_valid_signup():
    assert parse_signup(body(email=" friend@example.com ", sports=["soccer", "flag-football", "soccer"]), INVITE, ALLOWED) == (
        "friend@example.com",
        ["flag-football", "soccer"],
    )


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        body(invite="wrong"),
        body(invite=None),
        body(email="no-at-sign"),
        body(email="a@b"),
        body(email="x" * 250 + "@example.com"),
        body(sports=[]),
        body(sports="flag-football"),
        body(sports=["curling"]),
    ],
)
def test_rejects_bad_requests(raw):
    with pytest.raises(InvalidRequest):
        parse_signup(raw, INVITE, ALLOWED)


class FakeSns:
    def __init__(self, existing=None):
        self.subs = existing or []
        self.calls = []

    def get_paginator(self, name):
        subs = self.subs
        return type("P", (), {"paginate": lambda self, TopicArn: [{"Subscriptions": subs}]})()

    def subscribe(self, **kwargs):
        self.calls.append(("subscribe", kwargs))

    def set_subscription_attributes(self, **kwargs):
        self.calls.append(("set", kwargs))


@pytest.fixture
def lambda_env(monkeypatch):
    monkeypatch.setenv("TOPIC_ARN", "arn:topic")
    monkeypatch.setenv("ALLOWED_SPORTS", "flag-football,soccer")
    monkeypatch.setattr(subscribe, "_invite_code", INVITE)

    def call(sns, raw=None, method="POST"):
        monkeypatch.setattr(subscribe, "sns", sns)
        event = {"requestContext": {"http": {"method": method}}, "body": raw if raw is not None else body()}
        response = subscribe.handler(event, None)
        return response["statusCode"], json.loads(response["body"])

    return call


def test_new_email_subscribes_with_filter_policy(lambda_env):
    sns = FakeSns()
    status, data = lambda_env(sns)
    assert (status, data["status"]) == (200, "created")
    name, kwargs = sns.calls[0]
    assert name == "subscribe"
    assert kwargs["Protocol"] == "email"
    assert json.loads(kwargs["Attributes"]["FilterPolicy"]) == {"sport": ["flag-football"]}


def test_confirmed_email_gets_sports_updated(lambda_env):
    sns = FakeSns([{"Protocol": "email", "Endpoint": "Friend@Example.com", "SubscriptionArn": "arn:topic:abc"}])
    status, data = lambda_env(sns, body(sports=["soccer"]))
    assert data["status"] == "updated"
    assert sns.calls == [
        ("set", {"SubscriptionArn": "arn:topic:abc", "AttributeName": "FilterPolicy", "AttributeValue": '{"sport": ["soccer"]}'})
    ]


def test_pending_email_is_told_to_confirm(lambda_env):
    sns = FakeSns([{"Protocol": "email", "Endpoint": "friend@example.com", "SubscriptionArn": "PendingConfirmation"}])
    status, data = lambda_env(sns)
    assert data["status"] == "pending"
    assert sns.calls == []


def test_bad_invite_is_400_and_never_touches_sns(lambda_env):
    sns = FakeSns()
    status, data = lambda_env(sns, body(invite="nope"))
    assert status == 400
    assert "invite" in data["message"]
    assert sns.calls == []


def test_get_is_rejected(lambda_env):
    status, _ = lambda_env(FakeSns(), method="GET")
    assert status == 405
