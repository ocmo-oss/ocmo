"""Hand-written facade runtime: pagination and flat payload kwargs."""

from __future__ import annotations

import importlib
from typing import Any, cast

import attrs

from ocmo._bridge import (
    AsyncTransportBackedClient,
    TransportBackedClient,
    call_generated_async,
    call_generated_sync,
)
from ocmo._facade_meta import BODY_PAYLOADS, DEFAULT_PAGE_SIZE, DOCUMENT_BODY_OPS, PAGINATED
from ocmo._generated.types import UNSET


def _is_unset(value: Any) -> bool:
    return value is UNSET


def _coerce_limit(value: Any) -> int | None:
    if _is_unset(value):
        return None
    return int(value)


def _coerce_offset(value: Any) -> int:
    if _is_unset(value):
        return 0
    return int(value)


def _payload_class(module: str, class_name: str) -> type[Any]:
    return cast(type[Any], getattr(importlib.import_module(module), class_name))


def _build_body_payload(module: str, class_name: str, values: dict[str, Any]) -> Any:
    """Build a generated payload model, coercing nested dicts via ``from_dict``."""
    cls = _payload_class(module, class_name)
    from_dict = getattr(cls, "from_dict", None)
    if from_dict is not None:
        return from_dict(values)
    return cls(**values)


def _drop_unset(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if not _is_unset(value)}


def prepare_kwargs(operation_id: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Map flat SDK kwargs to generated-client kwargs (notably ``body``)."""
    out = dict(kwargs)

    if operation_id in DOCUMENT_BODY_OPS:
        body = out.pop("body", UNSET)
        content = out.pop("content", UNSET)
        if not _is_unset(body):
            out["body"] = body
        elif not _is_unset(content):
            out["body"] = content
        return _drop_unset(out)

    spec = BODY_PAYLOADS.get(operation_id)
    if spec is None:
        return _drop_unset(out)

    module, class_name, field_names = spec
    explicit_body = out.pop("body", UNSET)
    if not _is_unset(explicit_body):
        if isinstance(explicit_body, dict):
            out["body"] = _build_body_payload(module, class_name, explicit_body)
        else:
            out["body"] = explicit_body
        for field_name in field_names:
            out.pop(field_name, None)
        return _drop_unset(out)

    body_kwargs: dict[str, Any] = {}
    for name in field_names:
        if name in out:
            body_kwargs[name] = out.pop(name)

    if body_kwargs:
        out["body"] = _build_body_payload(module, class_name, body_kwargs)

    return _drop_unset(out)


def should_paginate(operation_id: str, kwargs: dict[str, Any]) -> bool:
    if operation_id not in PAGINATED:
        return False
    limit = _coerce_limit(kwargs.get("limit", UNSET))
    if limit is None:
        return False
    return limit > DEFAULT_PAGE_SIZE


def _merge_page(page: Any, items_attr: str, merged: list[Any]) -> Any:
    return attrs.evolve(page, **{items_attr: merged})


def paginate_sync(
    operation_id: str,
    detailed_fn: Any,
    *args: Any,
    client: TransportBackedClient,
    **kwargs: Any,
) -> Any:
    items_attr, count_attr = PAGINATED[operation_id]
    requested_limit = _coerce_limit(kwargs.get("limit", UNSET))
    assert requested_limit is not None

    offset = _coerce_offset(kwargs.get("offset", UNSET))
    remaining = requested_limit
    merged: list[Any] = []
    first_page: Any | None = None

    while remaining > 0:
        page_limit = min(remaining, DEFAULT_PAGE_SIZE)
        page_kwargs = {**kwargs, "limit": page_limit, "offset": offset}
        page = call_generated_sync(detailed_fn, *args, client=client, **page_kwargs)
        if first_page is None:
            first_page = page

        batch = list(getattr(page, items_attr))
        merged.extend(batch)
        total = int(getattr(page, count_attr))

        if len(batch) < page_limit or offset + len(batch) >= total:
            break

        offset += len(batch)
        remaining -= len(batch)

    assert first_page is not None
    return _merge_page(first_page, items_attr, merged)


async def paginate_async(
    operation_id: str,
    detailed_fn: Any,
    *args: Any,
    client: AsyncTransportBackedClient,
    **kwargs: Any,
) -> Any:
    items_attr, count_attr = PAGINATED[operation_id]
    requested_limit = _coerce_limit(kwargs.get("limit", UNSET))
    assert requested_limit is not None

    offset = _coerce_offset(kwargs.get("offset", UNSET))
    remaining = requested_limit
    merged: list[Any] = []
    first_page: Any | None = None

    while remaining > 0:
        page_limit = min(remaining, DEFAULT_PAGE_SIZE)
        page_kwargs = {**kwargs, "limit": page_limit, "offset": offset}
        page = await call_generated_async(detailed_fn, *args, client=client, **page_kwargs)
        if first_page is None:
            first_page = page

        batch = list(getattr(page, items_attr))
        merged.extend(batch)
        total = int(getattr(page, count_attr))

        if len(batch) < page_limit or offset + len(batch) >= total:
            break

        offset += len(batch)
        remaining -= len(batch)

    assert first_page is not None
    return _merge_page(first_page, items_attr, merged)


def execute_sync(
    operation_id: str,
    detailed_fn: Any,
    *args: Any,
    client: TransportBackedClient,
    **kwargs: Any,
) -> Any:
    prepared = prepare_kwargs(operation_id, kwargs)
    if should_paginate(operation_id, prepared):
        return paginate_sync(operation_id, detailed_fn, *args, client=client, **prepared)
    return call_generated_sync(detailed_fn, *args, client=client, **prepared)


async def execute_async(
    operation_id: str,
    detailed_fn: Any,
    *args: Any,
    client: AsyncTransportBackedClient,
    **kwargs: Any,
) -> Any:
    prepared = prepare_kwargs(operation_id, kwargs)
    if should_paginate(operation_id, prepared):
        return await paginate_async(operation_id, detailed_fn, *args, client=client, **prepared)
    return await call_generated_async(detailed_fn, *args, client=client, **prepared)
