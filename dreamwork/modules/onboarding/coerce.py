"""Turn messy human-typed strings into the typed values core expects.

Cap tables and pasted lists write money as "$2M" or "2,000,000", dates a dozen ways, and stage
as free text like "in convo". These helpers normalise all of that. They return None when they
can't parse — a blank is always allowed (spec §3.7), so a value we can't read is dropped, not
fatal.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from dreamwork.core.domain import Stage

_MONEY_RE = re.compile(r"^\s*\$?\s*([\d,.]+)\s*([kmb]?)\s*$", re.IGNORECASE)
_MULTIPLIER = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
_TRUE = {"yes", "y", "true", "1", "leads", "lead", "✓", "x"}
_FALSE = {"no", "n", "false", "0", ""}


def money_to_int(raw: object) -> int | None:
    """'$2M' -> 2000000, '2,000,000' -> 2000000, '500k' -> 500000."""
    if isinstance(raw, (int, float)):
        return int(raw)
    if not isinstance(raw, str):
        return None
    m = _MONEY_RE.match(raw)
    if not m:
        return None
    number, suffix = m.groups()
    number = number.replace(",", "")
    try:
        value = float(number)
    except ValueError:
        return None
    return int(value * _MULTIPLIER[suffix.lower()])


def to_date(raw: object) -> date | None:
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_bool(raw: object) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if not isinstance(raw, str):
        return None
    t = raw.strip().lower()
    if t in _TRUE:
        return True
    if t in _FALSE:
        return False
    return None


def to_list(raw: object) -> list[str] | None:
    """'climate, mobility' -> ['climate', 'mobility']. Splits on comma / semicolon / slash."""
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw]
    elif isinstance(raw, str):
        items = [p.strip() for p in re.split(r"[,;/]", raw)]
    else:
        return None
    items = [i for i in items if i]
    return items or None


# Free-text status -> the closest core Stage. See docs/pipeline.md for the canonical stages.
_STAGE_ALIASES: dict[Stage, tuple[str, ...]] = {
    Stage.SOURCED: ("sourced", "lead", "prospect", "backlog", "to contact", "new"),
    Stage.INTRO_REQUESTED: ("intro", "intro requested", "warm intro", "asked for intro"),
    Stage.CONTACTED: ("contacted", "reached out", "emailed", "outreach"),
    Stage.MEETING: ("meeting", "met", "call", "first meeting", "pitch"),
    Stage.IN_CONVERSATION: ("in conversation", "in convo", "conversation", "active", "engaged",
                            "discussing", "talking"),
    Stage.DILIGENCE: ("diligence", "dd", "due diligence", "deep dive"),
    Stage.COMMITTED: ("committed", "commit", "term sheet", "ts", "verbal", "soft circle", "in"),
    Stage.CLOSED: ("closed", "wired", "done", "signed", "funded"),
}


def to_stage(raw: object) -> Stage | None:
    if isinstance(raw, Stage):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None
    t = raw.strip().lower()
    for stage, aliases in _STAGE_ALIASES.items():
        if any(t == a for a in aliases):
            return stage
    for stage, aliases in _STAGE_ALIASES.items():
        if any(a in t for a in aliases):
            return stage
    return None
