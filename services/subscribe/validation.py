"""Check a sign-up request before it reaches SNS. Pure functions, no AWS calls."""

import hmac
import json
import re

# Deliberately loose: SNS's confirmation email is the real check that the address works.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_LENGTH = 254


class InvalidRequest(Exception):
    """The request is bad. The message is safe to show the user."""


def parse_signup(body: str, invite_code: str, allowed_sports: set[str]) -> tuple[str, list[str]]:
    """Return (email, sports) or raise InvalidRequest."""
    try:
        data = json.loads(body or "")
    except json.JSONDecodeError:
        raise InvalidRequest("Request body must be JSON.")
    if not isinstance(data, dict):
        raise InvalidRequest("Request body must be a JSON object.")

    # compare_digest takes the same time whether the first or last character differs,
    # so response timing does not leak how much of a guess was right.
    invite = data.get("invite")
    if not isinstance(invite, str) or not hmac.compare_digest(invite.encode(), invite_code.encode()):
        raise InvalidRequest("That invite link is not valid. Ask for a new one.")

    email = data.get("email")
    if not isinstance(email, str):
        raise InvalidRequest("Enter an email address.")
    email = email.strip()
    if len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email):
        raise InvalidRequest("That email address does not look right.")

    sports = data.get("sports")
    if not isinstance(sports, list) or not sports:
        raise InvalidRequest("Pick at least one sport.")
    if not all(isinstance(s, str) and s in allowed_sports for s in sports):
        raise InvalidRequest("Unknown sport.")

    return email, sorted(set(sports))
