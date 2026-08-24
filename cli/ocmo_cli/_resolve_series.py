"""Resolve-series time range and bucket helpers (mirrors frontend resolveStatsChart)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

DEFAULT_RESOLVE_RANGE = 30 * DAY
MIN_BUCKET_SECONDS = 1800


def pick_resolve_bucket_seconds(range_seconds: float) -> int:
    """Pick bucket size from visible range duration (see frontend thresholds)."""
    if range_seconds > 15 * DAY:
        return DAY
    if range_seconds > 5 * DAY:
        return 12 * HOUR
    if range_seconds > 3 * DAY:
        return 4 * HOUR
    if range_seconds > 1 * DAY:
        return 2 * HOUR
    if range_seconds >= 0.5 * DAY:
        return HOUR
    return 30 * MINUTE


def parse_cli_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp from a CLI flag."""
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def resolve_time_range(
    from_value: str | None,
    to_value: str | None,
) -> tuple[datetime, datetime]:
    """Default to the last 30 days ending now; override with --from / --to."""
    end = parse_cli_timestamp(to_value) if to_value else datetime.now(UTC)
    start = parse_cli_timestamp(from_value) if from_value else end - timedelta(seconds=DEFAULT_RESOLVE_RANGE)
    if start >= end:
        raise ValueError("--from must be earlier than --to.")
    return start, end


def resolve_bucket_seconds(
    start: datetime,
    end: datetime,
    *,
    override: int | None,
) -> int:
    if override is not None:
        if override < MIN_BUCKET_SECONDS:
            raise ValueError(f"--bucket-seconds must be at least {MIN_BUCKET_SECONDS}.")
        return override
    range_seconds = (end - start).total_seconds()
    return max(pick_resolve_bucket_seconds(range_seconds), MIN_BUCKET_SECONDS)


def series_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict"):
        return cast(dict[str, Any], result.to_dict())
    if isinstance(result, dict):
        return result
    return cast(dict[str, Any], vars(result))


def bucket_values(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[int], list[int], list[int]]:
    raw_buckets = data.get("buckets") or []
    buckets: list[dict[str, Any]] = []
    for item in raw_buckets:
        if isinstance(item, dict):
            buckets.append(item)
        elif hasattr(item, "to_dict"):
            buckets.append(item.to_dict())
        else:
            buckets.append(vars(item))
    direct = [int(b.get("direct") or 0) for b in buckets]
    nested = [int(b.get("nested") or 0) for b in buckets]
    errors = [int(b.get("errors") or 0) for b in buckets]
    return buckets, direct, nested, errors
