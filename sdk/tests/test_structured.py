"""Tests for structured property access (§10)."""

import pytest

from ocmo.errors import PropertyNotFoundError, UnstructuredFormatError
from ocmo.structured import _SENTINEL, StructuredMixin, path_get


class _FakeItem(StructuredMixin):
    """Minimal stub implementing the StructuredMixin contract."""

    def __init__(self, raw: bytes, fmt: str) -> None:
        self.name = "test"
        self.format = fmt
        self._raw = raw
        self._parsed_data: object = _SENTINEL

    def _get_bytes(self) -> bytes:
        return self._raw


# ---------------------------------------------------------------------------
# path_get
# ---------------------------------------------------------------------------


def test_simple_key():
    assert path_get({"a": 1}, "a") == 1


def test_nested_keys():
    assert path_get({"a": {"b": {"c": 42}}}, "a.b.c") == 42


def test_list_index():
    assert path_get({"servers": [{"port": 8080}]}, "servers[0].port") == 8080


def test_chained_indexes():
    assert path_get([[1, 2], [3, 4]], "[1][0]") == 3


def test_missing_raises_property_not_found():
    with pytest.raises(PropertyNotFoundError, match="missing"):
        path_get({"a": 1}, "missing")


def test_missing_with_default_returns_default():
    assert path_get({"a": 1}, "missing", default=99) == 99


def test_none_default_is_valid():
    """None as an explicit default must be returned, not confused with 'no default'."""
    result = path_get({"a": 1}, "missing", default=None)
    assert result is None


def test_none_value_in_data():
    """A None value in the data must be returned, not treated as missing."""
    assert path_get({"key": None}, "key") is None


# ---------------------------------------------------------------------------
# StructuredMixin
# ---------------------------------------------------------------------------


def test_json_parse():
    item = _FakeItem(b'{"host": "db.local", "port": 5432}', "json")
    assert item.data == {"host": "db.local", "port": 5432}


def test_yaml_parse():
    item = _FakeItem(b"host: db.local\nport: 5432\n", "yaml")
    assert item.data["host"] == "db.local"


def test_getitem():
    item = _FakeItem(b'{"key": "value"}', "json")
    assert item["key"] == "value"


def test_contains():
    item = _FakeItem(b'{"key": "value"}', "json")
    assert "key" in item
    assert "nope" not in item


def test_get_with_default():
    item = _FakeItem(b'{"a": 1}', "json")
    assert item.get("missing", default=42) == 42


def test_structured_access_on_raw_raises():
    item = _FakeItem(b"raw bytes", "raw")
    with pytest.raises(UnstructuredFormatError, match="raw"):
        _ = item.data


def test_structured_access_on_env_raises():
    item = _FakeItem(b"KEY=val", "env")
    with pytest.raises(UnstructuredFormatError, match="env"):
        _ = item.data


def test_parsing_is_memoised():
    calls = 0

    class _Counting(_FakeItem):
        def _get_bytes(self) -> bytes:
            nonlocal calls
            calls += 1
            return b'{"x": 1}'

    item = _Counting(b"", "json")
    _ = item.data
    _ = item.data
    assert calls == 1


def test_yaml_safe_loader_rejects_python_objects():
    """yaml.safe_load must NOT deserialise !!python/object tags."""
    payload = b"!!python/object/apply:os.system ['echo pwned']"
    item = _FakeItem(payload, "yaml")
    with pytest.raises(Exception):
        _ = item.data
