"""Shared pytest helpers for OCMO CLI tests."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

from click.testing import CliRunner, Result

from ocmo_cli.main import cli

_CLI_REGRESSION = re.compile(r"name '[^']+' is not defined|NameError|ImportError|IndentationError|AttributeError")


def mock_namespace_view(
    ctx: MagicMock,
    view: Any,
    *,
    namespace: str = "prod",
) -> None:
    """Wire a MagicMock OcmoCtx so ``namespace_view()`` returns *view*."""
    ctx.require_namespace.return_value = namespace
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view


def assert_help_excludes_io_flags(output: str) -> None:
    """Root/global -f/-o flags must not appear on subcommand help."""
    assert "  -f," not in output
    assert "  -o," not in output
    assert "  --file" not in output
    assert "  --output" not in output


def assert_no_cli_regression(result: Result) -> None:
    """Fail fast on obvious Python wiring bugs in command handlers."""
    combined = result.output + getattr(result, "stderr", "")
    if _CLI_REGRESSION.search(combined):
        raise AssertionError(f"CLI regression detected: {combined}")


@dataclass(frozen=True)
class SmokePaths:
    """Tree paths seeded for integration smoke tests."""

    root: str
    cfg: str
    template: str
    resolver: str

    @classmethod
    def under(cls, prefix: str) -> SmokePaths:
        root = prefix.rstrip("/")
        return cls(
            root=root,
            cfg=f"{root}/cfg.yaml",
            template=f"{root}/smoke.tpl",
            resolver=f"{root}/resolvers/smoke",
        )


@dataclass
class SmokeCli:
    """Invoke the real ``ocmo`` CLI against a live API."""

    namespace: str
    paths: SmokePaths = field(default_factory=lambda: SmokePaths.under("app"))
    gp_rule_id: str | None = None
    runner: CliRunner = field(default_factory=lambda: CliRunner(mix_stderr=False))

    def client(self, *args: str) -> Result:
        return self.runner.invoke(cli, list(args), catch_exceptions=False)

    def ns_cmd(self, *args: str) -> Result:
        return self.runner.invoke(cli, ["-n", self.namespace, *args], catch_exceptions=False)

    def global_dry_run(self, *args: str) -> Result:
        return self.runner.invoke(
            cli,
            ["--dry-run", "-n", self.namespace, *args],
            catch_exceptions=False,
        )

    def assert_ok(self, name: str, result: Result, *, allow_exit: set[int] | None = None) -> None:
        assert_no_cli_regression(result)
        allowed = allow_exit or {0}
        combined = result.output + getattr(result, "stderr", "")
        assert result.exit_code in allowed, f"{name} failed (exit {result.exit_code}, allowed {allowed}): {combined}"
