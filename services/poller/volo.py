"""The one HTTP call to Volo's GraphQL API. Stdlib only, so the Lambda needs no bundling."""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

from filters import FLAG_FOOTBALL_SPORT_ID

URL = "https://www.volosports.com/hapi/v1/graphql"
NYC_ORG_ID = "ff4d79f6-bba5-45dc-8532-46b8cf05f6e2"
QUERY = (Path(__file__).parent / "dropins.graphql").read_text()


def build_request_body(now: datetime, sport_id: str = FLAG_FOOTBALL_SPORT_ID, limit: int = 100) -> dict:
    """Open drop-ins for one sport in NYC that start after `now`."""
    where = {
        "_and": [
            {"organization_id": {"_eq": NYC_ORG_ID}},
            {"game_id": {"_is_null": False}},
            {
                "game": {
                    "start_time": {"_gte": now.isoformat()},
                    "drop_in_slots": {"is_available": {"_eq": True}},
                    "leagueByLeague": {
                        "organizationByOrganization": {"_id": {"_eq": NYC_ORG_ID}},
                        "archived": {"_eq": False},
                        "private": {"_eq": False},
                        "sportBySport": {"_id": {"_eq": sport_id}},
                    },
                }
            },
        ]
    }
    return {"operationName": "DropIns", "query": QUERY, "variables": {"where": where, "limit": limit}}


def fetch(body: dict, timeout: float = 15) -> dict:
    request = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "volo-dropin-notifier (personal use)"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
