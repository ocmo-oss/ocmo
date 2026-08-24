"""Load output format manifest and drive CLI -o/--output behavior."""

from __future__ import annotations

import functools
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import yaml

from ._output import (
    _as_table_rows,
    _infer_table_columns,
    emit,
    emit_table,
)
from ._sdk_dispatch import unwrap_list_payload
from ._typing import ClickDecorator

_MANIFEST_PATH = Path(__file__).with_name("output_formats.yaml")


@dataclass(frozen=True)
class FormatConfig:
    fields: list[str] | None = None
    infer_fields: bool = False
    mode: str | None = None
    hide_null_values: bool = False


@dataclass(frozen=True)
class CommandOutputSpec:
    command_key: str
    supported_formats: tuple[str, ...]
    default_tty: str
    default_non_tty: str
    fixed_default: str | None
    name_field: str
    table: FormatConfig | None
    wide: FormatConfig | None
    raw: FormatConfig | None


def command_key(action: str, resource: str | None = None) -> str:
    if resource:
        return f"{action} {resource}"
    return action


@functools.lru_cache(maxsize=1)
def _load_manifest() -> dict[str, Any]:
    with _MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest: {_MANIFEST_PATH}")
    return data


def _merge_profile(entry: dict[str, Any], profiles: dict[str, Any]) -> dict[str, Any]:
    profile_name = entry.get("profile")
    merged: dict[str, Any] = {}
    if profile_name:
        profile = profiles.get(profile_name)
        if isinstance(profile, dict):
            merged.update(profile)
    for key, value in entry.items():
        if key != "profile":
            merged[key] = value
    return merged


def _parse_format_config(data: dict[str, Any] | None) -> FormatConfig | None:
    if not data:
        return None
    raw_fields = data.get("fields")
    infer = raw_fields == "*"
    fields: list[str] | None
    if isinstance(raw_fields, list):
        fields = [str(item) for item in raw_fields]
    else:
        fields = None
    return FormatConfig(
        fields=fields,
        infer_fields=infer,
        mode=data.get("mode"),
        hide_null_values=bool(data.get("hide_null_values")),
    )


def _build_spec(command_key_value: str, entry: dict[str, Any]) -> CommandOutputSpec:
    supported = entry.get("supported_formats")
    if not isinstance(supported, list) or not supported:
        raise ValueError(f"Command {command_key_value!r} has no supported_formats")

    default_tty = str(entry.get("default_tty") or entry.get("default") or "table")
    default_non_tty = str(entry.get("default_non_tty") or entry.get("default") or "yaml")
    fixed_default = str(entry["default"]) if "default" in entry else None
    name_field = str(entry.get("name_field") or "name")

    return CommandOutputSpec(
        command_key=command_key_value,
        supported_formats=tuple(str(fmt) for fmt in supported),
        default_tty=default_tty,
        default_non_tty=default_non_tty,
        fixed_default=fixed_default,
        name_field=name_field,
        table=_parse_format_config(entry.get("table") if isinstance(entry.get("table"), dict) else None),
        wide=_parse_format_config(entry.get("wide") if isinstance(entry.get("wide"), dict) else None),
        raw=_parse_format_config(entry.get("raw") if isinstance(entry.get("raw"), dict) else None),
    )


@functools.cache
def get_command_spec(key: str) -> CommandOutputSpec:
    """Return merged output spec for a command key."""
    manifest = _load_manifest()
    profiles = manifest.get("profiles", {})
    commands = manifest.get("commands", {})

    if key in commands and not key.startswith("_"):
        entry = _merge_profile(dict(commands[key]), profiles)
        return _build_spec(key, entry)

    action = key.split(" ", 1)[0]
    generated_defaults = commands.get("_generated_defaults", {})
    if isinstance(generated_defaults, dict) and action in generated_defaults:
        base = dict(generated_defaults[action])
        entry = _merge_profile(base, profiles)
        return _build_spec(key, entry)

    entry = _merge_profile({"profile": "list_wide"}, profiles)
    return _build_spec(key, entry)


def supported_formats_help(spec: CommandOutputSpec) -> str:
    formats = [fmt for fmt in spec.supported_formats if fmt != "jsonpath"]
    return ", ".join(formats)


def output_formats_help(spec: CommandOutputSpec) -> str:
    """Help text listing base formats plus jsonpath field extraction."""
    listed = supported_formats_help(spec)
    return f"{listed}, or jsonpath=<path>"


def default_format_help(spec: CommandOutputSpec) -> str:
    if spec.fixed_default:
        return spec.fixed_default
    return f"{spec.default_tty} on TTY, {spec.default_non_tty} otherwise"


def output_option_help(spec: CommandOutputSpec) -> str:
    return (
        f"Output format: {output_formats_help(spec)} "
        f"to extract properties by dot-path. "
        f"Default: {default_format_help(spec)}."
    )


def is_valid_format(value: str, spec: CommandOutputSpec) -> bool:
    return value in spec.supported_formats or value.startswith("jsonpath=")


def validate_output_format(
    value: str | None,
    spec: CommandOutputSpec,
    *,
    ctx: click.Context | None = None,
    param: click.Parameter | None = None,
) -> str | None:
    if value is None:
        return value
    if is_valid_format(value, spec):
        return value
    valid = output_formats_help(spec)
    raise click.BadParameter(
        f"{value!r} is not a valid output format for {spec.command_key!r}. " f"Valid values: {valid}.",
        ctx=ctx,
        param=param,
    )


def resolve_effective_format(
    cli_fmt: str | None,
    ctx_fmt: str | None,
    spec: CommandOutputSpec,
) -> str:
    for candidate in (cli_fmt, ctx_fmt):
        if candidate is None:
            continue
        if is_valid_format(candidate, spec):
            return candidate
    if spec.fixed_default:
        return spec.fixed_default
    env = os.environ.get("OCMO_OUTPUT")
    if env:
        if is_valid_format(env, spec):
            return env
        print(
            f"Warning: OCMO_OUTPUT={env!r} is not valid for {spec.command_key!r}; ignored.",
            file=sys.stderr,
        )
    return spec.default_tty if sys.stdout.isatty() else spec.default_non_tty


def _combined_command_spec(command_keys: tuple[str, ...]) -> CommandOutputSpec:
    specs = [get_command_spec(key) for key in command_keys]
    supported = tuple(dict.fromkeys(fmt for spec in specs for fmt in spec.supported_formats))
    if not supported:
        raise ValueError(f"No supported formats for command keys: {command_keys!r}")
    primary = specs[0]
    return CommandOutputSpec(
        command_key=" / ".join(command_keys),
        supported_formats=supported,
        default_tty=primary.default_tty,
        default_non_tty=primary.default_non_tty,
        fixed_default=primary.fixed_default,
        name_field=primary.name_field,
        table=primary.table,
        wide=primary.wide,
        raw=primary.raw,
    )


def manifest_output_option(command_key_value: str) -> ClickDecorator:
    """Standard -o / --output flag configured from the manifest."""
    return manifest_output_option_for_keys(command_key_value)


def manifest_output_option_for_keys(*command_key_values: str) -> ClickDecorator:
    """``-o`` / ``--output`` flag validating against a union of command specs."""
    spec = (
        get_command_spec(command_key_values[0])
        if len(command_key_values) == 1
        else _combined_command_spec(command_key_values)
    )

    def _callback(
        ctx: click.Context,
        param: click.Parameter,
        value: str | None,
    ) -> str | None:
        return validate_output_format(value, spec, ctx=ctx, param=param)

    return click.option(
        "-o",
        "--output",
        "output_fmt",
        default=None,
        metavar="FORMAT",
        help=output_option_help(spec),
        callback=_callback,
        is_eager=False,
        expose_value=True,
    )


def columns_for_format(
    spec: CommandOutputSpec,
    fmt: str,
    rows: list[dict[str, Any]],
) -> list[str]:
    config = spec.table if fmt == "table" else spec.wide if fmt == "wide" else None
    if config is None:
        return _infer_table_columns(rows)
    if config.infer_fields or not config.fields:
        return _infer_table_columns(rows)
    return list(config.fields)


def _rows_from_data(
    data: Any,
    *,
    command_key: str | None = None,
    wide: bool = False,
) -> list[dict[str, Any]]:
    rows = unwrap_list_payload(data)
    if rows is None:
        rows = _as_table_rows(data)
    if command_key == "get globalpermission":
        from ._globalpermission_output import global_permission_table_rows

        return global_permission_table_rows(rows, wide=wide)
    if command_key == "whoami":
        from ._whoami_output import whoami_table_rows

        return whoami_table_rows(data)
    if command_key == "resolve parameters":
        from ._resolve_parameters_output import resolve_parameters_table_rows

        return resolve_parameters_table_rows(data)
    return rows


def emit_command_output(
    command_key_value: str,
    data: Any,
    fmt: str | None,
    *,
    ctx_fmt: str | None = None,
    columns_override: list[str] | None = None,
) -> None:
    """Emit command result using manifest-driven format resolution."""
    from ._output import _emit_identifiers

    spec = get_command_spec(command_key_value)
    effective_fmt = resolve_effective_format(fmt, ctx_fmt, spec)

    if effective_fmt in ("table", "wide"):
        rows = _rows_from_data(
            data,
            command_key=command_key_value,
            wide=effective_fmt == "wide",
        )
        columns = columns_override or columns_for_format(spec, effective_fmt, rows)
        emit_table(rows, columns)
        return

    if effective_fmt == "name":
        rows = _rows_from_data(data, command_key=command_key_value)
        _emit_identifiers(rows if rows else data, spec.name_field)
        return

    emit(data, effective_fmt)


def uses_document_profile(command_key_value: str) -> bool:
    return "raw" in get_command_spec(command_key_value).supported_formats
