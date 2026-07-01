"""qualified_list (owner: Chris) — qualification + the REAL Postgres store.

Two jobs (see docs/module-contracts.md):

  1. The real local Postgres implementation of `core.repository.Repository`. When it exists,
     everything else keeps working unchanged — that's the whole point of the contract. You also
     own how `dossier_path` is stored/generated (see core/dossiers.py).

  2. Qualification: turn the investor universe into "who it makes sense to talk to this round",
     filtering/scoring by round, ticket size, geography, sector, stage. A no or a next-round fit
     becomes an Outcome flag on the PipelineEntry, never a deletion (see docs/pipeline.md).

Nothing here is built yet. A starting shape:

    from dataclasses import dataclass
    from dreamwork.core.repository import Repository
    from dreamwork.core.domain import PipelineEntry

    @dataclass
    class QualificationCriteria:
        min_ticket_usd: int | None = None
        geographies: list[str] | None = None
        sectors: list[str] | None = None

    def qualify(repo: Repository, round_id: str, criteria: QualificationCriteria) -> list[PipelineEntry]:
        ...  # score firms, create/update PipelineEntry rows

    class PostgresRepository:  # implements core.repository.Repository
        ...

Ask your Claude: "Read CLAUDE.md and docs/, then help me build the Postgres Repository first,
so the rest of the team can run against a real database."
"""
