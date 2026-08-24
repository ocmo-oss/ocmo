import re
import secrets
from collections.abc import Mapping
from io import StringIO
from typing import TYPE_CHECKING, Any

import yaml  # pyyaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .exceptions import UploadTooLarge

if TYPE_CHECKING:
    pass

_TAG_NAME_PATTERN = r"^[a-zA-Z]{1}[a-zA-Z0-9_\.\+\-]{1,49}$"


def public_base_url(request: HttpRequest) -> str:
    """Return the public API base URL for absolute links in responses.

    Uses ``OCMO_PUBLIC_URL`` when configured (recommended behind a gateway);
    otherwise falls back to ``request.build_absolute_uri("/")``.
    """
    configured = getattr(settings, "OCMO_PUBLIC_URL", "") or ""
    if configured:
        return configured.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def validate_path_characters(path: str, *, allow_root: bool = False) -> None:
    """Raise ValidationError if *path* contains invalid characters or structure."""
    if path.startswith("/"):
        raise ValidationError("Path can't starts with '/'")
    if any(el.strip() == "" for el in path.removesuffix("/").split("/")) and not path == "":
        raise ValidationError("Path can't have path part that is empty or consist from spaces only")
    if not allow_root and path == "":
        raise ValidationError("Path can't be empty")
    segments = path.removesuffix("/").split("/") if path else []
    if not allow_root and any(seg in (".", "..") for seg in segments):
        raise ValidationError("Path segments '.' and '..' are not allowed")
    if not allow_root and not re.match(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$", path):
        raise ValidationError(
            "Path should consist of alphanumeric characters, underscores, and hyphens, and be separated by slashes"
        )


def validate_tag_name(tag: str) -> None:
    """Raise ValidationError when *tag* is not a valid version tag name."""
    if not re.match(_TAG_NAME_PATTERN, tag):
        raise ValidationError("Tag must match ^[a-zA-Z0-9_.+-]+$ and be 2-50 characters")
    if len(tag) > 50:
        raise ValidationError("Tag must be at most 50 characters")


def make_template_environment() -> SandboxedEnvironment:
    """Return a sandboxed Jinja2 environment for template parse/render."""
    return SandboxedEnvironment(
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def safe_yaml_load(data: str) -> Any:
    """Parse YAML with alias expansion disabled to mitigate billion-laughs DoS."""

    class _NoAliasLoader(yaml.SafeLoader):
        def ignore_aliases(self, data):
            return True

    return yaml.load(data, Loader=_NoAliasLoader)


def assert_upload_size(data: str, max_bytes: int, item_kind: str) -> None:
    """Raise UploadTooLarge when UTF-8 encoded size exceeds max_bytes (0 disables)."""
    if max_bytes <= 0:
        return
    size = len(data.encode("utf-8"))
    if size > max_bytes:
        raise UploadTooLarge(f"{item_kind} upload size {size} bytes exceeds the limit of {max_bytes} bytes")


def is_valid_positive_int(s):
    try:
        if int(s) > 0:
            return True
        return False
    except ValueError:
        return False


def generate_resolver_token():
    # Token is 32 symbols token that starts on "ocmort-" and then have random 25 alphanumerical symbols
    return "ocmort-" + secrets.token_urlsafe(25)


def mask_resolver_token(token: str | None) -> str | None:
    """Mask a resolver token for API reads (first nine characters + literal ****)."""
    if not token:
        return None
    return f"{token[:9]}****"


def is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def is_list(value: Any) -> bool:
    return isinstance(value, list) or isinstance(value, CommentedSeq)


def to_plain(value: Any) -> Any:
    """Convert ruamel CommentedMap/Seq into plain dict/list recursively."""

    if isinstance(value, CommentedMap):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, CommentedSeq):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    if isinstance(value, str):
        return str(value)
    return value


def resolve_relative_path(base_folder: str, ref_path: str) -> str:
    """Resolve ``./x`` or ``../x`` against ``base_folder`` (namespace root)."""

    if ref_path.startswith("./") or ref_path.startswith("../"):
        base_segments = [s for s in base_folder.split("/") if s] if base_folder else []
        ref_segments = ref_path.split("/")
        for seg in ref_segments:
            if seg == "..":
                if base_segments:
                    base_segments.pop()
            elif seg in ("", "."):
                continue
            else:
                base_segments.append(seg)
        return "/".join(base_segments)
    return ref_path.strip("/")


def config_path_relative_to_folder(config_path: str, folder_path: str) -> str:
    """Return *config_path* relative to a folder resolve root."""
    folder = folder_path.strip("/")
    if not folder:
        return config_path
    prefix = f"{folder}/"
    if config_path.startswith(prefix):
        return config_path[len(prefix) :]
    return config_path


def normalize_resolver_glob_pattern(pattern: str) -> str:
    """Normalize resolver include/exclude globs for folder-relative matching."""
    normalized = pattern.strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def match_resolver_glob(pattern: str, relative_path: str) -> bool:
    """Match a config path (relative to the resolved folder) against a resolver glob."""
    from .utils.permissions_compiler import PermissionsCompiler

    normalized = normalize_resolver_glob_pattern(pattern)
    if not normalized:
        return False
    regex_str, _slots = PermissionsCompiler.glob_to_regex(normalized)
    return re.fullmatch(regex_str, relative_path) is not None


def parse_ref(ref: str) -> tuple[str, str]:
    """Split ``path[@version]`` into ``(path, version_or_latest)``."""

    if "@" in ref:
        path, version = ref.rsplit("@", 1)
        return path, version or "latest"
    return ref, "latest"


def is_version_number_ref(ref: str) -> bool:
    """True when *ref* is an all-digit version number."""
    return bool(ref) and ref.isdigit()


def tag_subresource_from_ref(ref: str) -> tuple[str, str] | None:
    """Return (subresource_type, subresource) when *ref* is a tag name.

    All-digit refs → None (caller sets object_version instead).
    """
    if not ref or is_version_number_ref(ref):
        return None
    return "tag", ref


def traverse_field_path(data: Any, field_path: str) -> Any:
    """Return the value at a dot-separated field path (e.g. ``logging.log_level``)."""

    if not field_path or not is_mapping(data):
        return None
    cursor: Any = data
    for part in field_path.split("."):
        if not part or not is_mapping(cursor) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def delete_field_path(data: Any, field_path: str) -> None:
    """Remove the leaf key at a dot-separated field path; no-op when path is missing."""

    if not field_path or not is_mapping(data):
        return
    parts = field_path.split(".")
    if not parts or not parts[-1]:
        return
    cursor: Any = data
    for part in parts[:-1]:
        if not is_mapping(cursor) or part not in cursor:
            return
        cursor = cursor[part]
    if is_mapping(cursor):
        cursor.pop(parts[-1], None)


def apply_exclude_paths(data: Any, exclude_paths: list[str]) -> None:
    """Remove each exclude path from a mapping in place."""

    if not is_mapping(data):
        return
    for path in exclude_paths:
        delete_field_path(data, path)


def align_commented_map_key_order(target: CommentedMap, source: Mapping) -> None:
    """Reorder keys in *target* CommentedMap to match *source* key order, recursively.

    Keys from *source* that are present in *target* come first (in *source* order),
    followed by *target*-only keys in their original relative order.
    """
    if not isinstance(target, CommentedMap) or not source:
        return

    source_keys_in_target = [k for k in source if k in target]
    target_only_keys = [k for k in target if k not in source]
    new_order = source_keys_in_target + target_only_keys

    if list(target.keys()) != new_order:
        for k in new_order:
            target.move_to_end(k)

    for k in source_keys_in_target:
        child_target = target.get(k)
        child_source = source.get(k)
        if isinstance(child_target, CommentedMap) and child_source is not None and is_mapping(child_source):
            align_commented_map_key_order(child_target, child_source)


_yaml_preserve = YAML()
_yaml_preserve.preserve_quotes = True
_yaml_preserve.default_flow_style = False


def load_yaml_with_comments(data: str) -> Any:
    """Parse YAML preserving comments and formatting (ruamel)."""

    if not data or not data.strip():
        return CommentedMap()
    loaded = _yaml_preserve.load(data)
    if loaded is None:
        return CommentedMap()
    return loaded


def dump_yaml_with_comments(doc: Any) -> str:
    """Serialize a YAML document preserving comments where possible (ruamel)."""

    stream = StringIO()
    _yaml_preserve.dump(doc, stream)
    return stream.getvalue()


class SelectorLookupError(Exception):
    """Raised when a selector path is missing in data."""

    def __init__(self, expr: str, failure_kind: str) -> None:
        super().__init__(expr)
        self.expr = expr
        self.failure_kind = failure_kind  # "key" | "index"


def _tokenize_selector(expr: str) -> list[Any]:
    """Tokenise ``.a.b[0].c`` into ``['a', 'b', 0, 'c']``."""

    if not expr or not expr.startswith("."):
        raise ValueError(f"Selector must start with '.': {expr!r}")
    tokens: list[Any] = []
    for chunk in expr[1:].split("."):
        if not chunk:
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)(\[-?\d+\])*$", chunk)
        if not m:
            raise ValueError(f"Invalid selector segment {chunk!r}")
        tokens.append(chunk.split("[")[0])
        for idx in re.findall(r"\[(-?\d+)\]", chunk):
            tokens.append(int(idx))
    return tokens


def parse_selector(expr: str) -> tuple[str, bool]:
    """Parse selector expression, returning ``(normalized_expr, optional)``.

    A trailing ``?`` marks the selector as optional (missing paths yield defaults).
    """

    optional = expr.endswith("?")
    normalized = expr[:-1] if optional else expr
    _tokenize_selector(normalized)
    return normalized, optional


def validate_selector_syntax(expr: str) -> str:
    """Validate selector syntax; return normalized expression without optional ``?``."""

    normalized, _optional = parse_selector(expr)
    return normalized


def _default_for_missing(failure_kind: str) -> Any:
    return [] if failure_kind == "index" else {}


def _walk_selector(data: Any, tokens: list[Any], expr: str) -> Any:
    cursor: Any = data
    for tok in tokens:
        if cursor is None:
            raise SelectorLookupError(expr, "key")
        if isinstance(tok, int):
            if not is_list(cursor):
                raise SelectorLookupError(expr, "key")
            try:
                cursor = cursor[tok]
            except IndexError:
                raise SelectorLookupError(expr, "index") from None
        else:
            if not is_mapping(cursor):
                raise SelectorLookupError(expr, "key")
            if tok not in cursor:
                raise SelectorLookupError(expr, "key")
            cursor = cursor[tok]
    return cursor


def eval_selector(data: Any, expr: str, *, optional: bool = False) -> Any:
    """Evaluate selector on *data*; honour optional ``?`` suffix on *expr*."""

    normalized, is_optional = parse_selector(expr)
    use_optional = optional or is_optional
    tokens = _tokenize_selector(normalized)
    if not tokens:
        return data
    try:
        return _walk_selector(data, tokens, normalized)
    except SelectorLookupError as exc:
        if use_optional:
            return _default_for_missing(exc.failure_kind)
        raise


def embed_at_path(expr: str, value: Any) -> Any:
    """Build a nested document placing *value* at selector *expr*."""

    normalized = validate_selector_syntax(expr)
    tokens = _tokenize_selector(normalized)
    result: Any = value
    for tok in reversed(tokens):
        if isinstance(tok, int):
            padded: list[Any] = [{} for _ in range(tok)]
            padded.append(result)
            result = padded
        else:
            result = {tok: result}
    return result


def json_path(data: Any, expr: str) -> Any:
    """Evaluate a tiny JSONPath-like selector: ``.a.b`` or ``.a.b[0]``."""

    tokens = _tokenize_selector(expr)
    cursor: Any = data
    for tok in tokens:
        if cursor is None:
            return None
        if isinstance(tok, int):
            if not is_list(cursor):
                return None
            try:
                cursor = cursor[tok]
            except IndexError:
                return None
        else:
            if not is_mapping(cursor):
                return None
            cursor = cursor.get(tok)
    return cursor
