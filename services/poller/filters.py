"""Which drop-ins are worth publishing.

The GraphQL query already filters on Volo's side. These checks are a cheap second
line of defense in case the query or Volo's data changes. Sport is not checked
here: every sport is published, and each subscriber's SNS filter policy picks.
"""

from datetime import datetime


def is_open(dropin, now: datetime) -> bool:
    return dropin.start > now and dropin.spots >= 1
