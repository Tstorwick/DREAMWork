"""The book-face client contract, a local mock, and the sanitize valve.

`BookFaceClient` is the interface to the shared, portfolio-only store. Today the only
implementation is `LocalMockBookFace` (in-process, for the hackathon). Later, a Google Cloud
client implements the same Protocol and everything built here keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from dreamwork.core.domain import Firm

# Only these firm-level attributes may ever cross into the shared store. Anything about *you*,
# your company, or a specific conversation stays internal. This allowlist is the guardrail.
# NEVER add a founder's private opinion here: `founder_rating` is a per-founder private field
# and must stay local (see docs/onboarding-flow-proposal.md). test_never_share_founder_rating
# locks this — if you're tempted to add it, that's the leak Chris warned about.
SHAREABLE_FIRM_FIELDS = ("fund_size_usd", "aum_usd", "leads", "follows_on")


@dataclass
class SharedFact:
    """One firm-level fact contributed to the book-face, with attribution and confidence."""

    firm_name: str
    field: str          # e.g. "fund_size_usd"
    value: object       # e.g. 200_000_000
    owner: str          # the founder who contributed it
    connection: str     # who actually holds the relationship with this firm
    confidence: float = 0.5  # grows as founders corroborate the same value


def sanitize(firm: Firm, owner: str, connection: str) -> list[SharedFact]:
    """Reduce a private Firm row to only the firm-level facts that are safe to share.

    Returns one SharedFact per known shareable field. Nothing internal/private is included —
    only fields in SHAREABLE_FIRM_FIELDS that actually have a value.
    """
    facts: list[SharedFact] = []
    for field_name in SHAREABLE_FIRM_FIELDS:
        value = getattr(firm, field_name)
        if value is None:
            continue
        facts.append(SharedFact(
            firm_name=firm.name, field=field_name, value=value,
            owner=owner, connection=connection,
        ))
    return facts


class BookFaceClient(Protocol):
    """The shared book-face store. GCloud implements this later; today it's mocked."""

    def publish(self, fact: SharedFact) -> None: ...
    def facts_for_firm(self, firm_name: str) -> list[SharedFact]: ...
    def firms_known_by(self, connection: str) -> list[str]: ...


@dataclass
class LocalMockBookFace:
    """In-process stand-in for the shared store. Corroboration bumps confidence."""

    _facts: list[SharedFact] = field(default_factory=list)

    def publish(self, fact: SharedFact) -> None:
        # If someone already shared this same firm/field/value, corroborate instead of duplicate.
        for existing in self._facts:
            if (existing.firm_name, existing.field, existing.value) == (
                fact.firm_name, fact.field, fact.value
            ):
                existing.confidence = min(1.0, existing.confidence + 0.25)
                return
        self._facts.append(fact)

    def facts_for_firm(self, firm_name: str) -> list[SharedFact]:
        return [f for f in self._facts if f.firm_name == firm_name]

    def firms_known_by(self, connection: str) -> list[str]:
        return sorted({f.firm_name for f in self._facts if f.connection == connection})
