"""external (owner: TBD, built later) — the "book face" seam.

The sanitized, portfolio-only shared graph. Founders opt in to share **firm-level facts only**
(fund size, typical ticket, does-it-lead), each carrying who contributed it, who holds the
connection, and a confidence that grows as founders corroborate. It is only valuable because
it's a *closed* group — keep that boundary sacred.

This is the one place internal data crosses into the shared store, and it does so only through
`sanitize()`. Mocked locally now (`LocalMockBookFace`); a Google Cloud client drops in later
behind the same `BookFaceClient` contract — nothing built against it changes.

    DEFERRED: what triggers a fact being shared (opt-in per fact vs auto-sanitize) is owned by
    the onboarding partner and wired in later. We model the *shape* now so that decision doesn't
    reshape data.

See core/external.py isn't a thing — everything for this seam lives here and in client.py.
"""

from dreamwork.modules.external.client import (
    BookFaceClient,
    LocalMockBookFace,
    SharedFact,
    sanitize,
)

__all__ = ["BookFaceClient", "LocalMockBookFace", "SharedFact", "sanitize"]
