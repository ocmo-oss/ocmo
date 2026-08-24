"""ocmo whoami — show current identity."""

from __future__ import annotations

from .._client_commands import client_command

whoami_cmd = client_command(
    "whoami",
    help="Show the identity of the current authenticated principal.",
    manifest_key="whoami",
    method="whoami",
)
