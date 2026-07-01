"""Demo-data seeder — fills a Repository with a lifelike fundraising round.

Call `seed_demo(repo)` on a fresh (empty) Repository to make the web dashboard look
alive: one Seed round for a fictional company, a dozen investor firms with varied
realistic tags, one partner each, and a pipeline that exercises both axes of the model
(Stage *and* Outcome). This is throwaway demo content — nothing here is real, and it
writes only through the repo's public `add_*` methods, so it works against the in-memory
store today and the Postgres store later.
"""

from __future__ import annotations

from datetime import date

from dreamwork.core.domain import (
    Firm,
    IntroRequest,
    Outcome,
    Partner,
    PipelineEntry,
    Round,
    Stage,
)

# One row per firm. Each tuple carries the firm's structured "tag" fields plus the name
# of its lead partner and that partner's title. A loop below turns each row into a Firm +
# Partner pair; a separate table drives the round-specific pipeline state. Keeping the two
# apart mirrors the model: firm/partner facts are stable, pipeline state is per-round.
#
# (slug, firm_name, website, fund_size_usd, aum_usd, leads, geographies, sectors,
#  follows_on, ticket_range, still_investing, founder_rating, partner_name, partner_role)
_FIRMS = [
    ("bluepeak", "Blue Peak Ventures", "https://bluepeak.vc",
     120_000_000, 340_000_000, True, ["San Francisco, CA"], ["Fintech", "B2B SaaS"],
     True, (1_000_000, 4_000_000), True, 4, "Grace Whitfield", "Partner"),
    ("northgate", "Northgate Capital", "https://northgate.com",
     500_000_000, None, True, ["New York, NY"], ["Fintech", "Infrastructure"],
     True, (3_000_000, 10_000_000), True, None, "Daniel Osei", "General Partner"),
    ("cedar", "Cedar Fund", "https://cedar.fund",
     45_000_000, 90_000_000, False, ["Austin, TX"], ["B2B SaaS", "Developer Tools"],
     True, (500_000, 2_000_000), True, 3, "Priya Nair", "Partner"),
    ("harbor", "Harbor Angels", "https://harborangels.co",
     15_000_000, None, False, ["Boston, MA"], ["Climate", "Hardware"],
     False, (100_000, 500_000), True, None, "Marcus Lindqvist", "Managing Partner"),
    ("summit", "Summit Row", "https://summitrow.vc",
     200_000_000, 200_000_000, None, ["San Francisco, CA", "Remote"], ["AI", "B2B SaaS"],
     True, (2_000_000, 6_000_000), True, None, "Elena Vasquez", "Partner"),
    ("riverbend", "Riverbend Ventures", "https://riverbend.vc",
     80_000_000, None, True, ["Chicago, IL"], ["Fintech", "Marketplace"],
     True, (1_000_000, 3_000_000), True, 4, "Thomas Reilly", "Partner"),
    ("meridian", "Meridian Growth", "https://meridiangrowth.com",
     650_000_000, 1_200_000_000, True, ["London, UK"], ["Growth", "Fintech"],
     False, (5_000_000, 15_000_000), False, None, "Sofia Andersson", "Principal"),
    ("lantern", "Lantern Seed", "https://lantern.fund",
     30_000_000, None, False, ["Berlin, DE"], ["B2B SaaS", "Climate"],
     True, (250_000, 1_000_000), True, None, "Jonas Weber", "Partner"),
    ("orchard", "Orchard Partners", "https://orchard.partners",
     150_000_000, 400_000_000, None, ["Toronto, CA"], ["Consumer", "Fintech"],
     True, (1_500_000, 5_000_000), True, 2, "Amara Okafor", "Partner"),
    ("stonebridge", "Stonebridge Capital", "https://stonebridge.capital",
     90_000_000, None, False, ["Miami, FL"], ["Real Estate Tech", "Fintech"],
     True, (750_000, 2_500_000), True, None, "Victor Ramos", "General Partner"),
    ("keystone", "Keystone Ventures", "https://keystone.vc",
     110_000_000, 260_000_000, True, ["Seattle, WA"], ["AI", "Infrastructure"],
     True, (1_000_000, 3_500_000), True, None, "Hannah Cole", "Partner"),
    ("brightline", "Brightline Fund", "https://brightline.fund",
     22_000_000, None, False, ["Denver, CO"], ["Climate", "Hardware"],
     True, (200_000, 800_000), True, 3, "Owen Fitzgerald", "Partner"),
]

# Per-firm pipeline state for round "r1". Spread across every canonical Stage, and across
# all four Outcomes (most ACTIVE, plus one SNOOZED / PASSED / NEXT_ROUND to exercise the
# two-axis model). `snooze` is a future date only for the snoozed entry.
#
# (slug, stage, outcome, is_lead, ticket_estimate, first_contact, last_contact, next_step, snooze)
_PIPELINE = [
    ("bluepeak", Stage.DILIGENCE, Outcome.ACTIVE, True, 2_000_000,
     date(2026, 3, 10), date(2026, 6, 24),
     "Send updated data room access + cap table", None),
    ("northgate", Stage.COMMITTED, Outcome.ACTIVE, True, 4_000_000,
     date(2026, 2, 28), date(2026, 6, 26),
     "Confirm term sheet signature timing", None),
    ("cedar", Stage.IN_CONVERSATION, Outcome.ACTIVE, False, 1_000_000,
     date(2026, 4, 2), date(2026, 6, 20),
     "Follow up after partner meeting recap", None),
    ("harbor", Stage.MEETING, Outcome.ACTIVE, False, 250_000,
     date(2026, 5, 12), date(2026, 6, 18),
     "Schedule second call with the syndicate", None),
    ("summit", Stage.DILIGENCE, Outcome.ACTIVE, True, 2_500_000,
     date(2026, 3, 20), date(2026, 6, 25),
     "Answer their technical due-diligence questions", None),
    ("riverbend", Stage.CONTACTED, Outcome.ACTIVE, False, 1_500_000,
     date(2026, 6, 5), date(2026, 6, 22),
     "Send deck and request intro call", None),
    ("meridian", Stage.MEETING, Outcome.NEXT_ROUND, False, None,
     date(2026, 4, 15), date(2026, 6, 10),
     None, None),
    ("lantern", Stage.CONTACTED, Outcome.SNOOZED, False, 400_000,
     date(2026, 5, 1), date(2026, 6, 2),
     None, date(2026, 8, 15)),
    ("orchard", Stage.IN_CONVERSATION, Outcome.ACTIVE, False, 1_500_000,
     date(2026, 4, 8), date(2026, 6, 19),
     "Share latest revenue metrics", None),
    ("stonebridge", Stage.MEETING, Outcome.PASSED, False, None,
     date(2026, 4, 22), date(2026, 5, 30),
     None, None),
    ("keystone", Stage.SOURCED, Outcome.ACTIVE, False, 1_000_000,
     date(2026, 6, 15), date(2026, 6, 15),
     "Find a warm intro before reaching out", None),
    ("brightline", Stage.CLOSED, Outcome.ACTIVE, False, 500_000,
     date(2026, 2, 10), date(2026, 6, 12),
     "Countersign SAFE and add to cap table", None),
]


def seed_demo(repo) -> None:
    """Populate `repo` with a realistic demo Seed round for Uplift360.

    Inserts in referential order — the round and all firms/partners exist before any
    pipeline entry or intro request references them — so this works even against a
    foreign-key-enforcing (Postgres) store.
    """
    # 1. The round comes first: pipeline entries and intros point at it.
    repo.add_round(
        Round(
            id="r1",
            company="Uplift360",
            label="Seed",
            target_usd=2_500_000,
            opened_at=date(2026, 2, 1),
        )
    )

    # 2. Firms and their partners. Each partner is added right after its firm so an
    #    FK-enforcing store sees the parent row first.
    for (slug, name, website, fund_size, aum, leads, geos, sectors,
         follows_on, ticket, still_investing, rating, p_name, p_role) in _FIRMS:
        repo.add_firm(
            Firm(
                id=f"f_{slug}",
                name=name,
                website=website,
                fund_size_usd=fund_size,
                aum_usd=aum,
                leads=leads,
                geographies=geos,
                sectors=sectors,
                follows_on=follows_on,
                ticket_size_usd_range=ticket,
                still_investing=still_investing,
                founder_rating=rating,
            )
        )
        repo.add_partner(
            Partner(
                id=f"pt_{slug}",
                firm_id=f"f_{slug}",
                name=p_name,
                role=p_role,
            )
        )

    # 3. Pipeline entries — one per firm, now that firms and partners exist.
    for (slug, stage, outcome, is_lead, ticket, first_contact, last_contact,
         next_step, snooze) in _PIPELINE:
        repo.add_pipeline_entry(
            PipelineEntry(
                id=f"pe_{slug}",
                round_id="r1",
                firm_id=f"f_{slug}",
                partner_id=f"pt_{slug}",
                stage=stage,
                outcome=outcome,
                is_lead=is_lead,
                ticket_estimate_usd=ticket,
                first_contact_date=first_contact,
                last_contact_date=last_contact,
                next_step=next_step,
                snooze_until=snooze,
            )
        )

    # 4. Intro requests — a separate funnel; target firms already exist.
    repo.add_intro_request(
        IntroRequest(
            id="ir_keystone",
            round_id="r1",
            target_firm_id="f_keystone",
            target_partner_id="pt_keystone",
            asked_of="Rebecca Lin (Extantia)",
            channel="email",
            status="requested",
            requested_at=date(2026, 6, 16),
        )
    )
    repo.add_intro_request(
        IntroRequest(
            id="ir_riverbend",
            round_id="r1",
            target_firm_id="f_riverbend",
            target_partner_id="pt_riverbend",
            asked_of="Sam Patel (portfolio founder)",
            channel="email",
            status="requested",
            requested_at=date(2026, 6, 4),
        )
    )
