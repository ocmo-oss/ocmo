"""ocmo api-health — check API dependency health."""

from __future__ import annotations

from .._client_commands import client_command

api_health_cmd = client_command(
    "api-health",
    help="Check API dependency health (database, cache, and related backends).",
    manifest_key="api-health",
    method="health",
)
