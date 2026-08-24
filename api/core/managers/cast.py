"""Cast sub-feature: serialize resolved data to a target text format.

Implements the cast step from ``docs/resolving-cast-feature.md``: validate the
requested format and its options, then emit the structured data as YAML, JSON,
env, HCL, or raw text.

Entry point is :meth:`CastManager.cast`. The manager owns option schemas,
option coercion, and per-format emitters.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Mapping
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml import YAML

from ..exceptions import (
    CannotCast,
    InvalidCastOption,
    UnknownCastFormat,
    UnknownCastOption,
)
from ..schemas.cast_options import CAST_OPTION_FIELD_TYPES, validate_cast_options
from ..shortcuts import to_plain
from ..validation_errors import format_pydantic_validation_error


class CastManager:
    """Serialize resolved data into a target format.

    Parameters
    ----------
    format_name:
        Target format name (``yaml``, ``json``, ``env``, ``hcl``, ``raw``).
    options:
        Raw options dict (values may be strings from query params); will be
        coerced against the per-format schema.
    """

    def __init__(
        self,
        format_name: str,
        options: dict[str, Any] | None = None,
        *,
        source_label: str | None = None,
    ):
        self.format = format_name
        self.source_label = source_label
        self.options = self._normalize_options(format_name, options or {})

    # ----- public API -----

    def cast(self, data: Any) -> str:
        if self.format == "yaml":
            return self._cast_yaml(data)
        if self.format == "json":
            return self._cast_json(data)
        if self.format == "env":
            return self._cast_env(data)
        if self.format == "hcl":
            return self._cast_hcl(data)
        if self.format == "raw":
            return self._cast_raw(data)
        if self.format == "python":
            raise UnknownCastFormat("python cast is SDK-only and not available via REST")
        raise UnknownCastFormat(f"Unknown cast format {self.format!r}")

    # ----- option normalization -----

    @staticmethod
    def _normalize_options(fmt: str, options: dict[str, Any]) -> dict[str, Any]:
        if fmt == "python":
            raise UnknownCastFormat("python cast is SDK-only and not available via REST")
        field_types = CAST_OPTION_FIELD_TYPES.get(fmt)
        if field_types is None:
            raise UnknownCastFormat(f"Unknown cast format {fmt!r}")
        coerced: dict[str, Any] = {}
        for k, v in (options or {}).items():
            if k not in field_types:
                raise UnknownCastOption(f"Unknown option {k!r} for cast format {fmt!r}")
            coerced[k] = CastManager._coerce_option(v, field_types[k])
        try:
            return validate_cast_options(fmt, coerced)
        except PydanticValidationError as exc:
            raise InvalidCastOption("; ".join(format_pydantic_validation_error(exc))) from exc
        except ValueError as exc:
            raise InvalidCastOption(str(exc)) from exc

    @staticmethod
    def _coerce_option(value: Any, target_type: type) -> Any:
        if target_type is bool:
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in ("true", "1", "yes", "on"):
                return True
            if s in ("false", "0", "no", "off"):
                return False
            raise InvalidCastOption(f"Cannot coerce {value!r} to bool")
        if target_type is int:
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise InvalidCastOption(f"Cannot coerce {value!r} to int") from exc
        if target_type is str:
            return str(value)
        return value

    # ----- helpers shared across formats -----

    @staticmethod
    def _sorted_keys(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: CastManager._sorted_keys(value[k]) for k in sorted(value)}
        if isinstance(value, list):
            return [CastManager._sorted_keys(v) for v in value]
        return value

    @staticmethod
    def _json_prepare_data(data: Any, strict_keys: bool) -> Any:
        plain = to_plain(data)

        def walk(value: Any) -> Any:
            if isinstance(value, Mapping):
                if strict_keys:
                    for key in value:
                        if not isinstance(key, str):
                            raise InvalidCastOption(f"Non-string JSON key {key!r} (strict_keys=true)")
                    return {key: walk(item) for key, item in value.items()}
                return {str(key): walk(item) for key, item in value.items()}
            if isinstance(value, list):
                return [walk(item) for item in value]
            return value

        return walk(plain)

    # ----- YAML -----

    @staticmethod
    def _configure_yaml_emitter(ry: YAML, opts: dict[str, Any] | None = None) -> None:
        """Emit Python ``None`` as explicit YAML ``null`` (not a bare key)."""
        from ruamel.yaml.representer import RoundTripRepresenter

        # Reset mapping/sequence representers so flow-style handlers from a
        # prior cast cannot leak into later YAML emissions in the same process.
        ry.representer.add_representer(dict, RoundTripRepresenter.represent_dict)
        ry.representer.add_representer(list, RoundTripRepresenter.represent_list)

        def represent_none(representer, _data):
            return representer.represent_scalar("tag:yaml.org,2002:null", "null")

        ry.representer.add_representer(type(None), represent_none)

        cast_opts = opts or {}
        forced_style = cast_opts.get("default_scalar_style")

        def represent_str(representer, data: str):
            if forced_style:
                style = forced_style
            elif "\n" in data:
                style = "|"
            else:
                style = None
            return representer.represent_scalar("tag:yaml.org,2002:str", data, style=style)

        ry.representer.add_representer(str, represent_str)

        flow_style = cast_opts.get("flow_style", "block")
        if flow_style == "flow":

            def represent_dict(representer, data):
                return representer.represent_mapping(
                    "tag:yaml.org,2002:map",
                    data,
                    flow_style=True,
                )

            def represent_list(representer, data):
                return representer.represent_sequence(
                    "tag:yaml.org,2002:seq",
                    data,
                    flow_style=True,
                )

            ry.representer.add_representer(dict, represent_dict)
            ry.representer.add_representer(list, represent_list)

    def _cast_yaml(self, data: Any) -> str:
        opts = self.options
        ry = YAML()
        self._configure_yaml_emitter(ry, opts)
        ry.indent(
            mapping=opts.get("indent", 2),
            sequence=opts.get("indent", 2) + 2,
            offset=opts.get("indent", 2),
        )
        ry.width = opts.get("width", 0) or 4096
        ry.allow_unicode = opts.get("allow_unicode", True)
        ry.explicit_start = opts.get("explicit_start", False)
        ry.explicit_end = opts.get("explicit_end", False)
        flow_style = opts.get("flow_style", "block")
        if flow_style == "flow":
            ry.default_flow_style = True
        elif flow_style == "block":
            ry.default_flow_style = False
        else:
            ry.default_flow_style = None
        if opts.get("sort_keys"):
            data = self._sorted_keys(data)
        stream = io.StringIO()
        ry.dump(data, stream)
        out = stream.getvalue()
        if opts.get("trailing_newline", True) and not out.endswith("\n"):
            out += "\n"
        if not opts.get("trailing_newline", True) and out.endswith("\n"):
            out = out.rstrip("\n")
        return out

    # ----- JSON -----

    def _cast_json(self, data: Any) -> str:
        opts = self.options
        indent = opts.get("indent")
        separators = None
        sep_opt = opts.get("separators", "auto")
        if sep_opt == "compact":
            separators = (",", ":")
        elif sep_opt == "pretty":
            separators = (", ", ": ")
        prepared = self._json_prepare_data(data, opts.get("strict_keys", False))
        out = json.dumps(
            prepared,
            indent=indent if indent else None,
            sort_keys=opts.get("sort_keys", False),
            ensure_ascii=opts.get("ensure_ascii", False),
            allow_nan=opts.get("allow_nan", False),
            separators=separators,
        )
        if opts.get("trailing_newline", False):
            out += "\n"
        return out

    # ----- env -----

    @staticmethod
    def _flatten_for_env(
        data: Any,
        separator: str,
        prefix: str = "",
        *,
        list_format: str = "indexed",
        list_separator: str = ",",
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if isinstance(data, Mapping):
            for key, value in data.items():
                new_key = f"{prefix}{separator}{key}" if prefix else str(key)
                out.update(
                    CastManager._flatten_for_env(
                        value,
                        separator,
                        new_key,
                        list_format=list_format,
                        list_separator=list_separator,
                    )
                )
        elif isinstance(data, list):
            if not prefix:
                return out
            if list_format == "joined":
                out[prefix] = list_separator.join(str(item) for item in data)
            elif list_format == "json":
                out[prefix] = json.dumps(to_plain(data))
            elif list_format == "space":
                out[prefix] = " ".join(str(item) for item in data)
            else:
                for idx, value in enumerate(data):
                    new_key = f"{prefix}{separator}{idx}"
                    out.update(
                        CastManager._flatten_for_env(
                            value,
                            separator,
                            new_key,
                            list_format=list_format,
                            list_separator=list_separator,
                        )
                    )
        elif prefix:
            out[prefix] = data
        return out

    @staticmethod
    def _quote_env(value: Any, mode: str) -> str:
        s = "" if value is None else str(value)
        if mode == "never":
            return s
        if mode == "single":
            return "'" + s.replace("'", "'\\''") + "'"
        if mode == "double":
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
        # auto / always
        needs_quote = mode == "always" or bool(re.search(r"[ \t\"'$`\\;&|<>(){}*?!]", s)) or s == ""
        if needs_quote:
            return "'" + s.replace("'", "'\\''") + "'"
        return s

    @staticmethod
    def _format_env_bool(value: bool, mode: str) -> str:
        if mode == "upper":
            return "TRUE" if value else "FALSE"
        if mode == "numeric":
            return "1" if value else "0"
        if mode == "yesno":
            return "yes" if value else "no"
        if mode == "onoff":
            return "on" if value else "off"
        return "true" if value else "false"

    def _cast_env(self, data: Any) -> str:
        opts = self.options
        if not isinstance(data, (Mapping, list)):
            raise CannotCast("env cast requires a mapping or list at the document root")

        flat = self._flatten_for_env(
            data,
            opts.get("separator", "_"),
            list_format=opts.get("list_format", "indexed"),
            list_separator=opts.get("list_separator", ","),
        )

        if opts.get("uppercase"):
            flat = {k.upper(): v for k, v in flat.items()}
        elif opts.get("lowercase"):
            flat = {k.lower(): v for k, v in flat.items()}

        prefix = opts.get("prefix", "")
        if prefix:
            flat = {f"{prefix}{k}": v for k, v in flat.items()}

        if opts.get("sort_keys", False):
            flat = {k: flat[k] for k in sorted(flat)}

        bool_format = opts.get("bool_format", "lower")
        null_handling = opts.get("null_handling", "skip")
        quote_mode = opts.get("quote", "auto")
        dialect = opts.get("type", "unix")
        export = opts.get("export", True)
        escape_newlines = opts.get("escape_newlines", True)
        strict = opts.get("strict", True)

        lines: list[str] = []
        if opts.get("comment_header"):
            label = self.source_label or "resolve output"
            lines.append(f"# {label}")

        for key, value in flat.items():
            if strict and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                raise InvalidCastOption(f"Variable name {key!r} is not valid (set strict=false to sanitize)")
            if not strict:
                key = re.sub(r"[^A-Za-z0-9_]", "_", key)
                if not re.match(r"^[A-Za-z_]", key):
                    key = "_" + key

            if value is None:
                if null_handling == "skip":
                    continue
                if null_handling == "empty":
                    rendered = ""
                else:
                    rendered = "null"
            elif isinstance(value, bool):
                rendered = self._format_env_bool(value, bool_format)
            elif isinstance(value, (int, float)):
                rendered = str(value)
            else:
                rendered = str(value)
                if escape_newlines and "\n" in rendered:
                    rendered = rendered.replace("\n", "\\n")

            if dialect == "unix":
                quoted = self._quote_env(rendered, quote_mode)
                prefix_str = "export " if export else ""
                lines.append(f"{prefix_str}{key}={quoted}")
            elif dialect == "windows":
                lines.append(f'SET "{key}={rendered}"')
            elif dialect == "powershell":
                quoted = self._quote_env(rendered, "single" if quote_mode == "auto" else quote_mode)
                lines.append(f"$env:{key} = {quoted}")
            else:
                raise InvalidCastOption(f"Unknown env dialect {dialect!r}")

        sep = "\r\n" if dialect == "windows" else "\n"
        return sep.join(lines)

    # ----- HCL -----

    def _format_hcl_key(self, key: Any) -> str:
        key_text = str(key)
        if self.options.get("quote_keys"):
            return json.dumps(key_text, ensure_ascii=False)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", key_text):
            return key_text
        return json.dumps(key_text, ensure_ascii=False)

    def _format_hcl_string(self, value: str) -> str:
        if "\n" in value and self.options.get("heredoc_strings"):
            marker = "EOT" if self.options.get("version", "2") == "2" else "EOF"
            return f"<<-{marker}\n{value}\n{marker}"
        return json.dumps(value, ensure_ascii=False)

    def _cast_hcl_value(self, value: Any, indent: int, level: int = 0) -> str:
        """Minimal HCL emitter — handles scalars, lists, and dicts."""

        pad = " " * (indent * level)
        pad_inner = " " * (indent * (level + 1))
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return self._format_hcl_string(value)
        if isinstance(value, list):
            if not value:
                return "[]"
            items = [self._cast_hcl_value(item, indent, level + 1) for item in value]
            return "[\n" + ",\n".join(f"{pad_inner}{item}" for item in items) + f"\n{pad}]"
        if isinstance(value, Mapping):
            if not value:
                return "{}"
            items = []
            for key, item in value.items():
                key_str = self._format_hcl_key(key)
                items.append(f"{pad_inner}{key_str} = {self._cast_hcl_value(item, indent, level + 1)}")
            return "{\n" + "\n".join(items) + f"\n{pad}}}"
        return json.dumps(str(value))

    def _cast_hcl_block(self, value: Mapping[str, Any], indent: int, level: int = 0) -> str:
        pad = " " * (indent * level)
        pad_inner = " " * (indent * (level + 1))
        lines = []
        for key, item in value.items():
            key_str = self._format_hcl_key(key)
            if isinstance(item, Mapping):
                lines.append(f"{pad_inner}{key_str} {self._cast_hcl_block(item, indent, level + 1)}")
            else:
                lines.append(f"{pad_inner}{key_str} = {self._cast_hcl_value(item, indent, level + 1)}")
        return "{\n" + "\n".join(lines) + f"\n{pad}}}"

    def _cast_hcl(self, data: Any) -> str:
        opts = self.options
        indent = opts.get("indent", 2)
        if opts.get("sort_keys"):
            data = self._sorted_keys(data)
        if not isinstance(data, Mapping):
            raise CannotCast("hcl cast requires a mapping at the document root")

        if opts.get("tfvars"):
            flat = self._flatten_for_env(data, "_")
            lines = [f"{key} = {self._cast_hcl_value(value, indent, 0)}" for key, value in flat.items()]
        else:
            block_style = opts.get("block_style", "attribute")
            lines = []
            for key, value in data.items():
                key_str = self._format_hcl_key(key)
                if block_style == "block" and isinstance(value, Mapping):
                    lines.append(f"{key_str} {self._cast_hcl_block(value, indent, 1)}")
                else:
                    lines.append(f"{key_str} = {self._cast_hcl_value(value, indent, 0)}")

        out = "\n".join(lines)
        if opts.get("trailing_newline", True) and not out.endswith("\n"):
            out += "\n"
        return out

    # ----- raw -----

    def _cast_raw(self, data: Any) -> str:
        opts = self.options
        strict = opts.get("strict", True)
        if isinstance(data, (Mapping, list)):
            if strict:
                raise CannotCast("raw cast requires a scalar at the document root")
            if opts.get("stringify"):
                return yaml.safe_dump(to_plain(data))
            raise CannotCast("raw cast received non-scalar without stringify=true")
        out = "" if data is None else str(data)
        if opts.get("strip"):
            out = out.strip()
        encoding = opts.get("encoding", "utf-8")
        try:
            out = out.encode(encoding).decode(encoding)
        except LookupError as exc:
            raise InvalidCastOption(f"Unknown encoding {encoding!r}") from exc
        except UnicodeError as exc:
            raise InvalidCastOption(f"Value cannot be encoded as {encoding!r}") from exc
        if opts.get("trailing_newline", False) and not out.endswith("\n"):
            out += "\n"
        return out
