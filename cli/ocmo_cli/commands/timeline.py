"""ocmo timeline audit — item modification history as human-readable notes."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import click

from .._audit_item import resolve_audit_item
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._options import namespace_option
from .._output import as_dict, err, format_datetime

if TYPE_CHECKING:
    from ocmo import NamespaceView

_TIMELINE_PAGE_SIZE = 100

_AUDIT_HELP = """\
Show modification history for a tree item as human-readable notes.

\b
Examples:
  ocmo -n prod timeline audit app/web
  ocmo -n prod timeline audit app/web --search stable
  ocmo -n prod timeline audit app/web --limit 10
"""


def _reject_output_format(ctx: OcmoCtx) -> None:
    if ctx.output:
        raise click.UsageError("timeline audit does not support -o/--output or OCMO_OUTPUT for this command.")


def _fetch_timeline_entries(
    view: NamespaceView,
    *,
    path: str,
    node_type: str,
    search: str | None,
    limit: int | None = None,
) -> list[Any]:
    entries: list[Any] = []
    offset = 0
    while True:
        if limit is not None:
            remaining = limit - len(entries)
            if remaining <= 0:
                break
            page_limit = min(_TIMELINE_PAGE_SIZE, remaining)
        else:
            page_limit = _TIMELINE_PAGE_SIZE

        page = view.namespace_audit_timeline(
            object_id=path,
            object_type=node_type,
            search=search,
            limit=page_limit,
            offset=offset,
        )
        items = list(getattr(page, "items", []) or [])
        entries.extend(items)
        if limit is not None and len(entries) >= limit:
            return entries[:limit]
        total = int(getattr(page, "count", len(entries)))
        if not items or offset + len(items) >= total:
            break
        offset += len(items)
    return entries


def _entry_message(entry: Any) -> tuple[str, str]:
    data = as_dict(entry)
    occurred_at = format_datetime(data.get("occurred_at"))
    message = str(data.get("message") or "").strip()
    return occurred_at, message


@click.group("timeline", help="Item-scoped audit timelines.")
def timeline_group() -> None:
    """Timeline commands."""


@timeline_group.command("audit", help=_AUDIT_HELP)
@click.argument("address")
@click.option("--search", default=None, help="Filter notes (matches audit timeline search).")
@click.option("--limit", type=int, default=None, help="Maximum number of timeline events to show.")
@namespace_option()
@click.pass_obj
@sdk_command
def timeline_audit_cmd(
    ctx: OcmoCtx,
    address: str,
    search: str | None,
    limit: int | None,
    namespace: str | None,
) -> None:
    _reject_output_format(ctx)

    view, path, node_type = resolve_audit_item(
        ctx,
        address,
        namespace,
        command="timeline audit",
        allow_version_flag=True,
    )

    if limit is not None and limit < 1:
        err("--limit must be a positive integer.")
        raise SystemExit(USAGE_ERROR)

    entries = _fetch_timeline_entries(
        view,
        path=path,
        node_type=node_type,
        search=search,
        limit=limit,
    )

    if not entries:
        if sys.stdout.isatty():
            print("No audit events found.")
        return

    for entry in entries:
        occurred_at, message = _entry_message(entry)
        if occurred_at and message:
            print(f"{occurred_at}  {message}")
        elif message:
            print(message)
        elif occurred_at:
            print(occurred_at)
