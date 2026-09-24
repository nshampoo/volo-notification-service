# TODO

## Gendered drop-in spots

Coed drop-ins show a separate open-spot count per gender on Volo's site (confirmed 2026-09-23). We only fetch `game_drop_in_capacity.total_available_spots`, so an alert can go out for a spot the reader cannot take.

- Find the per-gender fields. Likely on `game_drop_in_capacity` or `drop_in_slots`. One or two small queries against the API should show them.
- Show the breakdown in the alert, e.g. "2 spots left (1 women, 1 any)".
- Add a `gender` message attribute and a sign-up option so SNS filter policies can match on it alongside `sport`.
- Also show the league type (coed, open, men, women) in the alert title. We already fetch `leagueByLeague.gender`.

## Smaller items

- MFA on root and on the `nick` IAM user.
- Volo app link: compare `links.volosports.com/game/<id>` with `/discover/daily-landing/?programId=<id>` on a future game and keep whichever opens the game more reliably.
- Dedup cost: check seen IDs with `BatchGetItem` before the conditional put. Only matters if polling gets more frequent than hourly.

## Later

- Web push notifications (home-screen web app, sender Lambda, VAPID keys). Needs Docker for `PythonFunction`.
- Filters for nights of the week and neighborhoods.
