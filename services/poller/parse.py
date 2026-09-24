"""Turn a raw Volo GraphQL response into DropIn records.

Anything unexpected raises VoloResponseError so the Lambda fails loudly and the
CloudWatch alarm fires, instead of quietly finding zero drop-ins forever.
"""

from dataclasses import dataclass
from datetime import datetime

GAME_URL = "https://www.volosports.com/game/{game_id}"


class VoloResponseError(Exception):
    pass


@dataclass(frozen=True)
class DropIn:
    game_id: str
    start: datetime  # timezone-aware, UTC
    spots: int
    sport_id: str
    sport: str
    league: str
    venue: str
    neighborhood: str | None

    @property
    def url(self) -> str:
        return GAME_URL.format(game_id=self.game_id)


def parse_response(payload: dict) -> list[DropIn]:
    if payload.get("errors"):
        raise VoloResponseError(f"GraphQL errors: {payload['errors']}")
    try:
        rows = payload["data"]["discover_daily"]
    except (KeyError, TypeError) as e:
        raise VoloResponseError(f"Missing data.discover_daily: {e!r}") from e
    if not isinstance(rows, list):
        raise VoloResponseError("data.discover_daily is not a list")
    return [_parse_row(row) for row in rows]


def _parse_row(row: dict) -> DropIn:
    try:
        game = row["game"]
        league = game["leagueByLeague"]
        venue = game["venueByVenue"]
        capacity = row.get("game_drop_in_capacity") or {}
        neighborhood = venue.get("neighborhoodByNeighborhoodId") or {}
        return DropIn(
            game_id=game["_id"],
            start=datetime.fromisoformat(game["start_time"]),
            spots=int(capacity.get("total_available_spots") or 0),
            sport_id=league["sportBySport"]["_id"],
            sport=league["sportBySport"]["name"],
            league=league["display_name"],
            venue=venue["shorthand_name"].strip(),
            neighborhood=neighborhood.get("name"),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise VoloResponseError(f"Unexpected row shape ({e!r}): {row.get('_id')}") from e
