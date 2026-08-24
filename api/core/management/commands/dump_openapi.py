"""Write the Ninja OpenAPI schema without a running HTTP server or OIDC provider."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Export GET /api/openapi.json from application code (no running server required)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output",
            "-o",
            default="-",
            help="Output file path (default: stdout).",
        )

    def handle(self, *args, **options) -> None:
        from ocmoapi.urls import api

        schema = api.get_openapi_schema()
        payload = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

        output = options["output"]
        if output == "-":
            self.stdout.write(payload, ending="")
            return

        path = Path(output)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            raise CommandError(f"Cannot write {path}: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))
