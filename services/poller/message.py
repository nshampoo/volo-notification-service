"""Notification text for a drop-in, in New York time."""

from zoneinfo import ZoneInfo

NYC = ZoneInfo("America/New_York")


def format_message(dropin) -> dict:
    local = dropin.start.astimezone(NYC)
    day = f"{local:%a %b} {local.day}"
    time = f"{local.hour % 12 or 12}:{local:%M %p}"
    place = f"{dropin.venue} ({dropin.neighborhood})" if dropin.neighborhood else dropin.venue
    spots = "1 spot" if dropin.spots == 1 else f"{dropin.spots} spots"
    return {
        "title": f"{dropin.sport} drop-in: {day}",
        "body": f"{time} at {place}. {spots} left.",
        "url": dropin.url,
    }
