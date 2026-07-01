# Pipeline: stages & outcomes

A conversation with an investor has **two independent axes**. Keeping them separate is what
lets us say "they passed this round but are a great next-round fit" without losing the record.

> **PROPOSED — please ratify.** These values are a starting proposal drawn from the meeting.
> The dashboard's reminders and the qualified-list logic key off them, so let's agree on the
> set before building on it. Edit here first; `core/domain.py` mirrors this file.

## Axis 1 — `Stage` (how far the conversation has progressed)

| Stage             | Meaning                                                        |
|-------------------|----------------------------------------------------------------|
| `sourced`         | On the qualified list, not yet contacted.                      |
| `intro_requested` | You've asked a mutual to introduce you (see IntroRequest).     |
| `contacted`       | Outreach sent / intro made; ball is in motion.                 |
| `meeting`         | A call/meeting is scheduled.                                   |
| `in_conversation` | You've met; active back-and-forth.                             |
| `diligence`       | They're doing diligence / deep engagement.                     |
| `committed`       | Verbal / soft-circle / term sheet.                             |
| `closed`          | Money wired.                                                   |

## Axis 2 — `Outcome` (the live status of the relationship)

| Outcome      | Meaning                                                              |
|--------------|---------------------------------------------------------------------|
| `active`     | Live in this round.                                                  |
| `snoozed`    | Deliberately parked until `snooze_until`; hidden from the dashboard. |
| `passed`     | They said no for this round. **Kept, not deleted.**                  |
| `next_round` | Not now, but a strong fit for a future round. "There's always another round." |

Why keep `passed` / `next_round` instead of deleting? The team was explicit: *"there's always
another round — you're always running from a larger set."* A no today is signal tomorrow.

## How the dashboard uses this
- **Needs a reply / follow-up:** `outcome == active` and (`next_step_due` is past, or
  `last_contact_date` older than a threshold), excluding anything `snoozed` until its date.
- **Round snapshot:** count/segment PipelineEntries by `stage`, weighted by `ticket_estimate_usd`
  and `is_lead`, to answer "where's my round?"
- **Auto-snooze:** move an entry to `snoozed` with a `snooze_until` when there's nothing to do yet.
