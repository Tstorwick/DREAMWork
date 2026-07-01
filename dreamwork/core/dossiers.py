"""Dossiers — the Markdown half of the data model.

Structured facts live in Postgres columns; everything freeform (sentiment, "what makes them
tick", call-prep notes, history) lives in a Markdown file per Firm/Partner, linked from the row
by `dossier_path`. cowork/Claude reads and edits these files directly, which is the whole point
of using Markdown.

This module is the *only* thing that reads/writes dossier files, so the storage convention
lives in one place.

    OWNED BY CHRIS: the final call on where dossiers live and how `dossier_path` is generated
    (files in-repo, a Postgres column, object storage) is Chris's, made alongside the DB. The
    file-based convention below is the working default so everything runs today.
"""

from __future__ import annotations

from pathlib import Path

# Dossiers are git-tracked files under data/dossiers/, grouped by entity kind.
DOSSIER_ROOT = Path("data/dossiers")


def dossier_path_for(kind: str, entity_id: str) -> str:
    """The conventional path for an entity's dossier, e.g. dossier_path_for('firm', 'f1')."""
    if kind not in {"firm", "partner"}:
        raise ValueError(f"unknown dossier kind {kind!r}")
    return str(DOSSIER_ROOT / kind / f"{entity_id}.md")


def read_dossier(path: str) -> str:
    """Return the dossier body, or '' if it doesn't exist yet."""
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_dossier(path: str, body: str, meta: dict[str, str] | None = None) -> None:
    """Write a dossier, with an optional YAML frontmatter block linking back to the row.

    `meta` typically carries the entity id so the file references its row (e.g. {"id": "f1"}).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = body
    if meta:
        front = "\n".join(f"{k}: {v}" for k, v in meta.items())
        content = f"---\n{front}\n---\n\n{body}"
    p.write_text(content, encoding="utf-8")
