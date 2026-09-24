"""Which drop-ins are worth a notification.

The GraphQL query already filters on Volo's side. These checks are a cheap second
line of defense in case the query or Volo's data changes.
"""

from datetime import datetime

FLAG_FOOTBALL_SPORT_ID = "6a4c2578-be2b-41cf-8b8a-f8c3ede1cfea"


def is_wanted(dropin, now: datetime) -> bool:
    return dropin.sport_id == FLAG_FOOTBALL_SPORT_ID and dropin.start > now and dropin.spots >= 1
