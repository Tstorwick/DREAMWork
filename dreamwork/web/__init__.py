"""web — a thin HTTP API in front of the Repository, plus the served dashboard UI.

The browser can't speak MCP (stdio), so this FastAPI layer exposes the same module logic
(dashboard/onboarding/qualified_list over a Repository) as JSON, and serves the static
prototype in prototypes/dashboard-web. Run: uvicorn dreamwork.web.api:app
"""
