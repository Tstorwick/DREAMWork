"""core — the shared foundation. Everything in DreamWork talks to core, never to each other.

Public surface:
    domain      entities + enums (Firm, Partner, Round, PipelineEntry, IntroRequest, Stage, Outcome)
    repository  the Repository Protocol — the data-access contract
    memory_store an in-memory Repository so the app runs with no database
    dossiers    read/write the Markdown dossier linked to each row
"""
