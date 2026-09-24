# TODO

## Gendered drop-in spots

Coed drop-ins show a separate open-spot count per gender on Volo's site (confirmed 2026-09-23). We only fetch `game_drop_in_capacity.total_available_spots`, so an alert can go out for a spot the reader cannot take.

- Find the per-gender fields. Likely on `game_drop_in_capacity` or `drop_in_slots`. One or two small queries against the API should show them.
- Show the breakdown in the alert, e.g. "2 spots left (1 women, 1 any)".
- Add a `gender` message attribute and a sign-up option so SNS filter policies can match on it alongside `sport`.
- Also show the league type (coed, open, men, women) in the alert title. We already fetch `leagueByLeague.gender`.

## Re-alert when a seen game gets more spots

Dedup is per game: a game alerts once, then its row blocks it until a day after the game. If spots go up later (1 to 3, or full then reopened), nobody hears about it.

- Store the last seen spot count on the dedup row.
- Alert again when the count goes up, not when it goes down.
- Consider a quiet period so a game flapping between 0 and 1 does not alert every hour.

## Smaller items

- If alerts get noisy, switch to one digest email per sport per run. Must be per sport, not per person: a message tagged with several sports would match anyone subscribed to any of them.

- MFA on root and on the `nick` IAM user.
- Volo app link: compare `links.volosports.com/game/<id>` with `/discover/daily-landing/?programId=<id>` on a future game and keep whichever opens the game more reliably.
- Dedup cost: check seen IDs with `BatchGetItem` before the conditional put. Only matters if polling gets more frequent than hourly.

## Text messages (SMS) instead of email

SNS can send SMS, and a sign-up could subscribe a phone number with the same `sport` filter policy. The catch is that US SMS is not free or instant to set up:

- Sending to US numbers requires a registered origination number. A toll-free number is the simplest: a monthly fee plus a verification that can take days to weeks. 10DLC is the other option, with brand and campaign registration.
- New accounts start in the SMS sandbox: only up to 10 pre-verified phone numbers. Leaving it takes a support request.
- Each message costs a fraction of a cent plus carrier fees. Small, but not always-free like email, and outside the "costs roughly nothing" goal. Check whether the Free plan allows it at all.
- Set an SNS monthly SMS spend limit so a burst cannot run up a bill.
- Sign-up page would need phone number validation, and SNS SMS opt-out ("STOP") handling.

Web push (below) gets alerts onto a phone for free, so compare the two before starting.

## Later

- Web push notifications (home-screen web app, sender Lambda, VAPID keys). Needs Docker for `PythonFunction`.
- Filters for nights of the week and neighborhoods.
