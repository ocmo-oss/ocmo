"""Tests for ``ocmo resolve draft``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ocmo_cli._exit import USAGE_ERROR
from ocmo_cli.commands.resolve_draft import resolve_draft_cmd
from ocmo_cli.main import cli


def test_resolve_draft_help_has_file_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["resolve", "draft", "--help"])
    assert result.exit_code == 0, result.output
    assert "  -f," in result.output or "--file" in result.output
    assert "stdin" in result.output.lower()
    assert "--cast" in result.output
    assert "--field" not in result.output


def test_resolve_draft_requires_file_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-n", "prod", "resolve", "draft", "app/web"])
    assert result.exit_code == USAGE_ERROR
    assert "Missing option '-f'" in result.output or "Missing option '--file'" in result.output


def test_resolve_draft_calls_api_with_file_content(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body_file = tmp_path / "draft.yaml"  # type: ignore[operator]
    body_file.write_text("key: draft-value\n")

    view = MagicMock()
    result = MagicMock()
    result.__iter__ = lambda self: iter([])
    view._namespace = "prod"
    view._client = MagicMock()

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.no_color = True

    captured: dict[str, object] = {}

    def fake_call_resolve_draft(
        view_arg: object,
        path: str,
        *,
        content: str,
        **kwargs: object,
    ) -> MagicMock:
        captured["view"] = view_arg
        captured["path"] = path
        captured["content"] = content
        captured["kwargs"] = kwargs
        return result

    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_draft.call_resolve_draft",
        fake_call_resolve_draft,
    )
    monkeypatch.setattr(
        "ocmo_cli.commands.resolve.run_resolve_pipeline",
        lambda *_args, **_kwargs: None,
    )

    runner = CliRunner()
    result_cli = runner.invoke(
        resolve_draft_cmd,
        ["app/web", "-f", str(body_file), "--cast", "yaml", "--param", "x=1"],
        obj=ctx,
    )

    assert result_cli.exit_code == 0, result_cli.output
    assert captured["path"] == "app/web"
    assert captured["content"] == "key: draft-value\n"
    assert captured["kwargs"] == {
        "cast": "yaml",
        "trace_only": False,
        "params": {"x": "1"},
        "cast_options": None,
    }


def test_resolve_draft_reads_stdin_when_file_is_dash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = MagicMock()
    result = MagicMock()
    result.__iter__ = lambda self: iter([])

    ctx = MagicMock()
    ctx.require_namespace.return_value = "prod"
    ctx.ns.return_value = view
    ctx.namespace_view.return_value = view
    ctx.output = None
    ctx.no_color = True

    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "ocmo_cli.commands.resolve_draft.call_resolve_draft",
        lambda _view, path, *, content, **_: captured.update({"path": path, "content": content}) or result,
    )
    monkeypatch.setattr(
        "ocmo_cli.commands.resolve.run_resolve_pipeline",
        lambda *_args, **_kwargs: None,
    )
    runner = CliRunner()
    result_cli = runner.invoke(
        resolve_draft_cmd,
        ["app/web", "-f", "-"],
        obj=ctx,
        input="stdin_key: from_stdin\n",
    )

    assert result_cli.exit_code == 0, result_cli.output
    assert captured["path"] == "app/web"
    assert captured["content"] == "stdin_key: from_stdin\n"


def test_call_resolve_draft_posts_yaml_and_builds_result() -> None:
    from ocmo_cli._resolve_draft import call_resolve_draft

    response = MagicMock()
    response.headers = {"X-Ocmo-Resolve-Cache": "miss"}
    response.json.return_value = {
        "length": 1,
        "trace_only": False,
        "items": [
            {
                "name": "web",
                "version": 0,
                "format": "yaml",
                "url": "http://example.test/api/v1/~download/token",
                "checksum": "sha256:abc",
                "trace": {},
            }
        ],
    }

    transport = MagicMock()
    transport.request.return_value = response

    client = MagicMock()
    client._transport = transport
    client._http = MagicMock()
    client._config.server = "http://example.test"

    view = MagicMock()
    view._namespace = "prod"
    view._client = client

    with patch("ocmo.resolve.build_resolve_result") as build_result:
        build_result.return_value = "resolve-result"
        result = call_resolve_draft(
            view,
            "app/web",
            content="key: draft\n",
            cast="yaml",
            params={"replicas": "3"},
        )

    assert result == "resolve-result"
    transport.request.assert_called_once()
    call_kwargs = transport.request.call_args.kwargs
    assert call_kwargs["content"] == "key: draft\n"
    assert call_kwargs["headers"] == {"Content-Type": "application/yaml"}
    assert call_kwargs["params"]["cast"] == "yaml"
    assert call_kwargs["params"]["param_replicas"] == "3"
