"""The one HTTP call to Volo's GraphQL API. Stdlib only, so the Lambda needs no bundling."""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

URL = "https://www.volosports.com/hapi/v1/graphql"
NYC_ORG_ID = "ff4d79f6-bba5-45dc-8532-46b8cf05f6e2"
QUERY = (Path(__file__).parent / "dropins.graphql").read_text()


# About 80 drop-ins are open at a typical time, so this leaves lots of headroom.
LIMIT = 500


def build_request_body(now: datetime, limit: int = LIMIT) -> dict:
    """Open drop-ins for every sport in NYC that start after `now`."""
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
