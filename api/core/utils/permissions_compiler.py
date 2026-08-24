"""Compile permission documents into efficient in-memory structures.

Documents are compiled once per version and stored in a bounded per-process
LRU. All subsequent evaluations run against pre-compiled matchers without
additional DB I/O on the hot path.

Cache keys
----------
Namespace ABAC policies : (namespace_id, permissions_version_number)
Global Permission rules  : (rule_count, max_updated_at_ms)

Entries are immutable once stored. Old entries become unreachable after a
version change and are evicted naturally by the LRU.
"""

from __future__ import annotations

import ipaddress
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from django.conf import settings

from ..exceptions import BrokenNamespace
from ..shortcuts import safe_yaml_load

# ---------------------------------------------------------------------------
# Compiled data structures
# ---------------------------------------------------------------------------


@dataclass
class CompiledResource:
    """Pre-compiled resource pattern for one glob string."""

    pattern: re.Pattern
    # Tuple of (group_name, kind, attribute) triples for interpolation slots.
    slots: tuple

    def matches(self, path: str, auth) -> bool:
        """Return True if path matches this resource pattern for the identity."""
        m = self.pattern.fullmatch(path)
        if m is None:
            return False
        for group, kind, attr in self.slots:
            try:
                matched_val = m.group(group)
            except IndexError:
                return False
            if kind == "user":
                claim_val = auth.get_claim(attr)
                if claim_val is None:
                    return False
                expected = PermissionsCompiler.sanitize_claim_for_path(claim_val)
            elif kind == "resolver":
                if attr == "name":
                    rname = auth.resolver_name
                    if rname is None:
                        return False
                    expected = PermissionsCompiler.sanitize_claim_for_path(rname)
                else:
                    return False
            else:
                return False
            if matched_val != expected:
                return False
        return True


@dataclass
class CompiledActors:
    """Pre-compiled actor matchers for one policy or global-rule gate."""

    # Each dict is {claim_name: value_or_WILDCARD}; matched with AND.
    # Multiple dicts are matched with OR.
    user_claim_sets: list[dict[str, str]]
    # Exact resolver tree paths; "*" matches any resolver.
    resolver_paths: frozenset
    # True when any user actor has all-wildcard claims (matches any user).
    wildcard_user: bool

    def matches_user(self, auth) -> bool:
        if self.wildcard_user:
            return auth.is_user
        user_claims = auth.claims
        for claim_set in self.user_claim_sets:
            if all(
                PermissionsCompiler._user_claim_matches(
                    claim_key,
                    expected,
                    auth,
                    user_claims,
                )
                for claim_key, expected in claim_set.items()
            ):
                return True
        return False

    def matches_resolver(self, auth) -> bool:
        if "*" in self.resolver_paths:
            return auth.is_resolver
        rpath = auth.resolver_path
        return rpath is not None and rpath in self.resolver_paths


@dataclass
class CompiledConditions:
    """Pre-compiled conditions for a policy."""

    ip_networks: list  # ipaddress.IPv4Network / IPv6Network objects
    time_ranges: list[tuple[int, int]]  # (start_minute_UTC, end_minute_UTC)

    def matches(self, request_ctx: dict | None) -> bool:
        """Return True when all conditions are satisfied.

        ip_range is conservatively denied when request_ctx carries no 'ip' key.
        time_of_day always uses datetime.now(UTC) when context has no 'time'.
        """
        if self.ip_networks:
            ip_str = (request_ctx or {}).get("ip")
            if not ip_str:
                return False  # cannot verify — conservative deny
            try:
                addr = ipaddress.ip_address(ip_str)
                if not any(addr in net for net in self.ip_networks):
                    return False
            except ValueError:
                return False

        if self.time_ranges:
            now: datetime = (request_ctx or {}).get("time") or datetime.now(UTC)
            minute = now.hour * 60 + now.minute
            if not any(start <= minute < end for start, end in self.time_ranges):
                return False

        return True


@dataclass
class CompiledPolicy:
    """One fully compiled namespace ABAC policy."""

    effect: str  # "Allow" | "Deny"
    actors: CompiledActors
    resources: list[CompiledResource]
    conditions: CompiledConditions

    def _actor_matches(self, auth) -> bool:
        if auth.is_user:
            return self.actors.matches_user(auth)
        if auth.is_resolver:
            return self.actors.matches_resolver(auth)
        return False

    def matches(self, path: str, auth, request_ctx: dict | None) -> bool:
        return (
            self._actor_matches(auth)
            and any(r.matches(path, auth) for r in self.resources)
            and self.conditions.matches(request_ctx)
        )


@dataclass
class BucketPair:
    deny: list[CompiledPolicy] = field(default_factory=list)
    allow: list[CompiledPolicy] = field(default_factory=list)


@dataclass
class CompiledPolicySet:
    """Namespace ABAC compiled from one _permissions config version.

    buckets[action_type][action_verb] → BucketPair(deny, allow)
    """

    buckets: dict[str, dict[str, BucketPair]]

    def get_candidates(self, action_type: str, action_verb: str) -> BucketPair:
        """Collect deny + allow policies relevant to (type, verb) including wildcards."""
        deny: list[CompiledPolicy] = []
        allow: list[CompiledPolicy] = []
        for t in (action_type, "*"):
            for v in (action_verb, "*"):
                pair = self.buckets.get(t, {}).get(v)
                if pair:
                    deny.extend(pair.deny)
                    allow.extend(pair.allow)
        return BucketPair(deny=deny, allow=allow)


@dataclass
class CompiledGlobalRule:
    """One compiled Global Permission rule (first-match-wins semantics)."""

    name_pattern: re.Pattern  # case-insensitive namespace name glob
    slots: tuple  # (group_name, kind, attribute) for {!user.X} interpolation
    read_actors: CompiledActors
    write_actors: CompiledActors
    delete_actors: CompiledActors
    audit_actors: CompiledActors

    def matches_namespace(self, namespace_name: str, auth) -> bool:
        """Return True when namespace_name matches this rule's pattern for auth."""
        m = self.name_pattern.fullmatch(namespace_name)
        if m is None:
            return False
        for group, kind, attr in self.slots:
            try:
                matched_val = m.group(group)
            except IndexError:
                return False
            if kind == "user":
                claim_val = auth.get_claim(attr)
                if claim_val is None:
                    return False
                expected = PermissionsCompiler.sanitize_claim_for_path(claim_val)
            else:
                return False
            if matched_val != expected:
                return False
        return True


@dataclass
class CompiledGlobalRules:
    """All Global Permission rules in evaluation order."""

    rules: list[CompiledGlobalRule]


class _LRUCache:
    """Thread-safe bounded LRU cache. Max size read from Django settings."""

    def __init__(self, size_setting: str, default_size: int) -> None:
        self._size_setting = size_setting
        self._default_size = default_size
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    @property
    def _max_size(self) -> int:
        return getattr(settings, self._size_setting, self._default_size)

    def get(self, key: tuple):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key: tuple, value) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = value
                return
            self._data[key] = value
            max_size = self._max_size
            while len(self._data) > max_size:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_EMPTY_POLICY_SET = CompiledPolicySet(buckets={})
_EMPTY_GLOBAL_RULES = CompiledGlobalRules(rules=[])

_USER_CLAIM_PLACEHOLDER_RE = re.compile(r"^\{!user\.([a-zA-Z0-9_]+)\}$")


class PermissionsCompiler:
    """Stateless compiler and cache for namespace and global permission documents."""

    _MAX_GLOB_PATTERN_LEN = 512
    _NAMESPACE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
    _NAMESPACE_NAME_MAX_LEN = 150

    _policy_cache: _LRUCache = _LRUCache("OCMO_PERMISSIONS_CACHE_SIZE", 1024)
    _global_cache: _LRUCache = _LRUCache("OCMO_PERMISSIONS_CACHE_SIZE", 32)

    @staticmethod
    def validate_user_claim_value(value: str) -> None:
        """Raise ValueError when a claim value uses an invalid placeholder."""
        if "{!" not in value:
            return
        if _USER_CLAIM_PLACEHOLDER_RE.fullmatch(value):
            return
        if value.startswith("{!resolver."):
            raise ValueError(f"Claim value {value!r} may not use resolver placeholders")
        raise ValueError(f"Invalid claim placeholder {value!r}; use {{!user.<claim>}} only")

    @staticmethod
    def resolve_user_claim_placeholder(value: str, auth) -> Any:
        """Resolve a claim expected value, expanding {{!user.<claim>}} from auth."""
        if value == "*":
            return "*"
        match = _USER_CLAIM_PLACEHOLDER_RE.fullmatch(value)
        if match is None:
            return value
        claim_val = auth.get_claim(match.group(1))
        if claim_val is None:
            return None
        return claim_val

    @staticmethod
    def _user_claim_matches(
        claim_key: str,
        expected: str,
        auth,
        user_claims: dict[str, Any],
    ) -> bool:
        if expected == "*":
            return True
        resolved = PermissionsCompiler.resolve_user_claim_placeholder(expected, auth)
        if resolved is None:
            return False
        actual = user_claims.get(claim_key)
        if actual is None:
            return False
        if isinstance(resolved, list):
            if isinstance(actual, list):
                return bool(set(actual) & set(resolved))
            return actual in resolved
        if isinstance(actual, list):
            return resolved in actual
        return actual == resolved

    @staticmethod
    def sanitize_claim_for_path(value: Any) -> str:
        """Sanitize a JWT claim value for path-component comparison."""
        s = str(value) if not isinstance(value, str) else value
        s = s.split("\n")[0].strip().lower()
        return re.sub(r"[^a-z0-9_\-]", "-", s)

    @staticmethod
    def is_catch_all_namespace_pattern(pattern: str) -> bool:
        """Return True when the namespace glob matches any namespace name."""
        return pattern in ("*", "**")

    @staticmethod
    def glob_to_regex(pattern: str) -> tuple[str, dict[str, tuple[str, str]]]:
        """Convert an OCMO resource glob to a regex string + interpolation slot metadata."""
        if len(pattern) > PermissionsCompiler._MAX_GLOB_PATTERN_LEN:
            raise ValueError(
                f"Glob pattern exceeds maximum length of {PermissionsCompiler._MAX_GLOB_PATTERN_LEN} characters"
            )
        slots: dict[str, tuple[str, str]] = {}
        slot_counter = 0
        parts: list[str] = []
        i = 0

        while i < len(pattern):
            if pattern[i : i + 2] == "{!":
                end = pattern.find("}", i + 2)
                if end == -1:
                    parts.append(re.escape(pattern[i]))
                    i += 1
                    continue
                token = pattern[i + 2 : end]
                segs = token.split(".", 1)
                if len(segs) == 2 and segs[0] in ("user", "resolver"):
                    kind, attr = segs[0], segs[1]
                    group = f"slot_{slot_counter}"
                    slot_counter += 1
                    slots[group] = (kind, attr)
                    parts.append(f"(?P<{group}>[a-z0-9_\\-]*)")
                else:
                    parts.append(re.escape(pattern[i : end + 1]))
                i = end + 1

            elif pattern[i] == "/" and pattern[i + 1 : i + 4] == "**/":
                parts.append("/(?:[^/]+/)*")
                i += 4

            elif pattern[i : i + 2] == "**":
                parts.append(".*")
                i += 2

            elif pattern[i] == "*":
                parts.append("[^/]+")
                i += 1

            elif pattern[i] == "?":
                parts.append("[^/]")
                i += 1

            else:
                parts.append(re.escape(pattern[i]))
                i += 1

        return "^" + "".join(parts) + "$", slots

    @staticmethod
    def _compile_actors(actors_raw: list[dict]) -> CompiledActors:
        user_claim_sets: list[dict[str, str]] = []
        resolver_paths: set[str] = set()
        wildcard_user = False

        for actor in actors_raw:
            kind = actor.get("kind", "")
            if kind == "User":
                claims: dict[str, str] = actor.get("claims", {})
                for claim_value in claims.values():
                    PermissionsCompiler.validate_user_claim_value(claim_value)
                if not claims or all(v == "*" for v in claims.values()):
                    wildcard_user = True
                user_claim_sets.append(claims)
            elif kind == "Resolver":
                resolver_paths.add(actor.get("path", "*"))

        return CompiledActors(
            user_claim_sets=user_claim_sets,
            resolver_paths=frozenset(resolver_paths),
            wildcard_user=wildcard_user,
        )

    @staticmethod
    def _compile_resources(resources_raw: list[str]) -> list[CompiledResource]:
        compiled: list[CompiledResource] = []
        for glob in resources_raw:
            regex_str, slots_dict = PermissionsCompiler.glob_to_regex(glob)
            try:
                pattern = re.compile(regex_str)
            except re.error:
                continue  # skip malformed (validation step should have caught this)
            slot_tuples = tuple((group, kind, attr) for group, (kind, attr) in slots_dict.items())
            compiled.append(CompiledResource(pattern=pattern, slots=slot_tuples))
        return compiled

    @staticmethod
    def _compile_conditions(raw: dict | None) -> CompiledConditions:
        if not raw:
            return CompiledConditions(ip_networks=[], time_ranges=[])

        ip_networks = []
        for cidr in raw.get("ip_range", []):
            try:
                ip_networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                pass

        time_ranges: list[tuple[int, int]] = []
        for window in raw.get("time_of_day", []):
            try:
                start_str, end_str = window.split("-", 1)
                sh, sm = map(int, start_str.strip().split(":"))
                eh, em = map(int, end_str.strip().split(":"))
                time_ranges.append((sh * 60 + sm, eh * 60 + em))
            except (ValueError, AttributeError):
                pass

        return CompiledConditions(ip_networks=ip_networks, time_ranges=time_ranges)

    @staticmethod
    def _compile_one_policy(policy_raw: dict) -> CompiledPolicy | None:
        effect = policy_raw.get("effect", "Allow")
        if effect not in ("Allow", "Deny"):
            return None
        return CompiledPolicy(
            effect=effect,
            actors=PermissionsCompiler._compile_actors(policy_raw.get("actors", [])),
            resources=PermissionsCompiler._compile_resources(policy_raw.get("resources", [])),
            conditions=PermissionsCompiler._compile_conditions(policy_raw.get("conditions")),
        )

    @staticmethod
    def compile_policy_set(doc: dict) -> CompiledPolicySet:
        """Compile a _permissions document dict into a CompiledPolicySet.

        Raises ValueError on malformed glob patterns (used as validation on write).
        """
        buckets: dict[str, dict[str, BucketPair]] = {}

        for policy_raw in doc.get("policies", []):
            compiled = PermissionsCompiler._compile_one_policy(policy_raw)
            if compiled is None:
                continue
            for action_str in policy_raw.get("actions", []):
                type_, _, verb = action_str.partition(":")
                verb = verb or "*"
                buckets.setdefault(type_, {}).setdefault(verb, BucketPair())
                pair = buckets[type_][verb]
                if compiled.effect == "Deny":
                    pair.deny.append(compiled)
                else:
                    pair.allow.append(compiled)

        return CompiledPolicySet(buckets=buckets)

    @staticmethod
    def _validate_namespace_glob_slots(
        ns_glob: str,
        slots: dict[str, tuple[str, str]],
    ) -> None:
        for kind, _attr in slots.values():
            if kind == "resolver":
                raise ValueError(f"Namespace glob {ns_glob!r} may not use resolver placeholders")

    @staticmethod
    def expand_namespace_pattern(pattern: str, auth) -> str | None:
        """Expand {!user.<claim>} tokens to a concrete namespace name, or None."""
        if "{!" not in pattern:
            return pattern
        _regex_str, slots = PermissionsCompiler.glob_to_regex(pattern)
        if not slots:
            return pattern
        result = pattern
        for _group, (kind, attr) in slots.items():
            if kind != "user":
                return None
            claim_val = auth.get_claim(attr)
            if claim_val is None:
                return None
            token = f"{{!user.{attr}}}"
            result = result.replace(
                token,
                PermissionsCompiler.sanitize_claim_for_path(claim_val),
                1,
            )
        if len(result) > PermissionsCompiler._NAMESPACE_NAME_MAX_LEN:
            return None
        if not PermissionsCompiler._NAMESPACE_NAME_RE.fullmatch(result):
            return None
        return result

    @staticmethod
    def validate_global_rules_order(rule_dicts: list[dict]) -> None:
        """Raise ValueError when a catch-all namespace pattern is not the last rule."""
        if not rule_dicts:
            return
        for index, rule in enumerate(rule_dicts):
            ns_glob = rule.get("namespace", "*")
            if PermissionsCompiler.is_catch_all_namespace_pattern(ns_glob) and index != len(rule_dicts) - 1:
                raise ValueError(
                    f"Catch-all namespace pattern {ns_glob!r} must be the last rule "
                    f"(found at position {index + 1} of {len(rule_dicts)})"
                )

    @staticmethod
    def compile_global_rules(rule_dicts: list[dict]) -> CompiledGlobalRules:
        """Compile an ordered list of Global Permission rule dicts.

        Raises ValueError on invalid namespace glob patterns.
        """
        PermissionsCompiler.validate_global_rules_order(rule_dicts)
        compiled_rules: list[CompiledGlobalRule] = []
        for rule in rule_dicts:
            ns_glob = rule.get("namespace", "*")
            if "[" in ns_glob or "]" in ns_glob:
                raise ValueError(f"Invalid namespace glob {ns_glob!r}: brackets are not allowed")
            regex_str, slots_dict = PermissionsCompiler.glob_to_regex(ns_glob)
            PermissionsCompiler._validate_namespace_glob_slots(ns_glob, slots_dict)
            try:
                name_pattern = re.compile(regex_str, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid namespace glob {ns_glob!r}: {exc}") from exc

            slot_tuples = tuple((group, kind, attr) for group, (kind, attr) in slots_dict.items())

            def _actors(section: dict | None) -> CompiledActors:
                return PermissionsCompiler._compile_actors((section or {}).get("actors", []))

            compiled_rules.append(
                CompiledGlobalRule(
                    name_pattern=name_pattern,
                    slots=slot_tuples,
                    read_actors=_actors(rule.get("read")),
                    write_actors=_actors(rule.get("write")),
                    delete_actors=_actors(rule.get("delete")),
                    audit_actors=_actors(rule.get("audit")),
                )
            )
        return CompiledGlobalRules(rules=compiled_rules)

    @staticmethod
    def load_policy_set(namespace) -> CompiledPolicySet:
        """Return the compiled policy set for namespace's active _permissions version."""
        from ..managers.tree import TreeManager

        perm_config = TreeManager(namespace, "_permissions", auth=None).get_item("config")
        if perm_config is None:
            raise BrokenNamespace(f"Broken namespace: {namespace.name}")

        tag = namespace.permissions_tag or "latest"
        version_number = perm_config.tags.get(tag)
        if version_number is None:
            raise BrokenNamespace(f"Broken namespace: {namespace.name}")

        cache_key = (namespace.id, version_number)
        cached = PermissionsCompiler._policy_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            version_obj = TreeManager.resolve_version(perm_config, tag)
            raw: dict = safe_yaml_load(version_obj.data) or {}
        except Exception:  # noqa: BLE001
            raise BrokenNamespace(f"Broken namespace: {namespace.name}")

        compiled = PermissionsCompiler.compile_policy_set(raw)
        PermissionsCompiler._policy_cache.put(cache_key, compiled)
        return compiled

    @staticmethod
    def load_global_rules() -> CompiledGlobalRules:
        """Return compiled Global Permission rules (cached by count + max updated_at)."""
        from ..managers.global_permissions import GlobalPermissionsManager

        count, latest_ms = GlobalPermissionsManager.cache_signature()
        if count == 0:
            return _EMPTY_GLOBAL_RULES

        cache_key = (count, latest_ms)

        cached = PermissionsCompiler._global_cache.get(cache_key)
        if cached is not None:
            return cached

        compiled = PermissionsCompiler.compile_global_rules(GlobalPermissionsManager.ordered_rule_dicts())
        PermissionsCompiler._global_cache.put(cache_key, compiled)
        return compiled
