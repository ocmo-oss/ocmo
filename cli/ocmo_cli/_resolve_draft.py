"""Resolve-draft API call returning a lazy :class:`ocmo.resolve.ResolveResult`."""

from __future__ import annotations

from typing import Any


def call_resolve_draft(
    view: Any,
    path: str,
    *,
    content: str,
    cast: str | None = None,
    trace_only: bool = False,
    no_creds: bool = False,
    params: dict[str, str] | None = None,
    cast_options: dict[str, str] | None = None,
) -> Any:
    """POST draft YAML to ``~resolve-draft`` and build a :class:`ResolveResult`."""
    from ocmo.client import _build_params, _encode_resolve_path
    from ocmo.resolve import build_resolve_result

    client = view._client
    wire_cast = "json" if cast == "python" else cast
    query = _build_params(
        params=params,
        cast_options=cast_options,
        extra={
            "cast": wire_cast,
            "trace_only": str(trace_only).lower() if trace_only else None,
            "no-creds": str(no_creds).lower() if no_creds else None,
        },
    )
    url = f"/ns/{view._namespace}/~resolve-draft/{_encode_resolve_path(path)}"
    resp = client._transport.request(
        "POST",
        url,
        params=query,
        content=content,
        headers={"Content-Type": "application/yaml"},
    )
    cache_status = resp.headers.get("X-Ocmo-Resolve-Cache")
    return build_resolve_result(
        resp.json(),
        http=client._http,
        transport=client._transport,
        server_origin=client._config.server,
        cast=cast,
        cache_status=cache_status,
    )
