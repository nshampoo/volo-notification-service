"""Pure poller logic: parsing, filtering, message text. Fixture data is made up."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from filters import is_open
from message import format_message
from parse import VoloResponseError, parse_response

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "volo_dropins.json").read_text())
BEFORE_GAMES = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def test_parse_reads_every_row():
    dropins = parse_response(FIXTURE)
    assert [d.game_id for d in dropins] == ["game-flag-open", "game-flag-full", "game-soccer-open"]
    first = dropins[0]
    assert first.spots == 2
    assert first.sport == "Flag Football"
    assert first.venue == "Test Field"  # trailing space stripped
    assert first.neighborhood == "Test Village"
    assert first.url == "https://www.volosports.com/game/game-flag-open"


def test_parse_treats_missing_capacity_as_zero_spots():
    assert parse_response(FIXTURE)[1].spots == 0


def test_parse_raises_on_graphql_errors():
    with pytest.raises(VoloResponseError):
        parse_response({"errors": [{"message": "field not found"}]})


def test_parse_raises_on_changed_shape():
    with pytest.raises(VoloResponseError):
        parse_response({"data": {"something_else": []}})
    with pytest.raises(VoloResponseError):
        parse_response({"data": {"discover_daily": [{"_id": "x", "game": {"_id": "x"}}]}})


def test_parse_reads_sport_slug_for_filter_policies():
    assert [d.sport_slug for d in parse_response(FIXTURE)] == ["flag-football", "flag-football", "soccer"]


def test_filter_keeps_open_future_games_of_any_sport():
    wanted = [d.game_id for d in parse_response(FIXTURE) if is_open(d, BEFORE_GAMES)]
    assert wanted == ["game-flag-open", "game-soccer-open"]


def test_filter_drops_games_that_already_started():
    after = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    assert not any(is_open(d, after) for d in parse_response(FIXTURE))


def test_message_uses_new_york_time():
    msg = format_message(parse_response(FIXTURE)[0])
    # 23:15 UTC on Oct 1 is 7:15 PM EDT.
    assert msg == {
        "title": "Flag Football drop-in: Thu Oct 1",
        "body": "7:15 PM at Test Field (Test Village). 2 spots left.",
        "url": "https://www.volosports.com/game/game-flag-open",
    }


def test_message_single_spot():
    dropin = parse_response(FIXTURE)[2]
    assert format_message(dropin)["body"] == "6:00 PM at Other Field (Test Heights). 1 spot left."

