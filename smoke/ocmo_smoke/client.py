"""Thin HTTP client for OCMO API smoke tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import requests


@dataclass
class ApiResponse:
    status_code: int
    body: Any
    text: str
    headers: dict = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class OcmoApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | str | None = None,
        content_type: Optional[str] = None,
        files: Optional[dict] = None,
        expected_json: bool = True,
    ) -> ApiResponse:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        resp = self._session.request(
            method,
            self._url(path),
            data=data,
            files=files,
            headers=headers or None,
            timeout=self.timeout,
        )
        text = resp.text
        if expected_json and text:
            try:
                body = resp.json()
            except json.JSONDecodeError:
                body = None
        else:
            body = text
        return ApiResponse(
            status_code=resp.status_code,
            body=body,
            text=text,
            headers=dict(resp.headers),
        )

    def create_namespace(self, name: str, description: str = "smoke test") -> ApiResponse:
        return self.request(
            "POST",
            "/api/v1/ns/",
            data=json.dumps({"name": name, "description": description}),
            content_type="application/json",
        )

    def delete_namespace(self, name: str) -> ApiResponse:
        return self.request("DELETE", f"/api/v1/ns/{name}")

    def create_config(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~config/~create/{path}",
            data=data,
            content_type=content_type,
        )

    def update_config(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "PUT",
            f"/api/v1/ns/{namespace}/~config/~update/{path}",
            data=data,
            content_type=content_type,
        )

    def create_template(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "text/plain",
    ) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~template/~create/{path}",
            data=data,
            content_type=content_type,
        )

    def update_template(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "text/plain",
    ) -> ApiResponse:
        return self.request(
            "PUT",
            f"/api/v1/ns/{namespace}/~template/~update/{path}",
            data=data,
            content_type=content_type,
        )

    def create_secret(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~secret/~create/{path}",
            data=data,
            content_type=content_type,
        )

    def update_secret(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "PUT",
            f"/api/v1/ns/{namespace}/~secret/~update/{path}",
            data=data,
            content_type=content_type,
        )

    def create_resolver(
        self,
        namespace: str,
        path: str,
        data: bytes | str = "",
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~resolver/~create/{path}",
            data=data,
            content_type=content_type,
        )

    def update_resolver(
        self,
        namespace: str,
        path: str,
        data: bytes | str,
        *,
        content_type: str = "application/yaml",
    ) -> ApiResponse:
        return self.request(
            "PUT",
            f"/api/v1/ns/{namespace}/~resolver/~update/{path}",
            data=data,
            content_type=content_type,
        )

    def rotate_resolver_token(
        self, namespace: str, path: str, token_number: int
    ) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~resolver/~rotate-token/{path}",
            data=json.dumps({"token_number": token_number}),
            content_type="application/json",
        )

    def get_item(
        self, namespace: str, path: str, *, version: str = "latest", reveal: bool = False
    ) -> ApiResponse:
        params: list[str] = []
        if version != "latest":
            params.append(f"version={version}")
        if reveal:
            params.append("reveal=true")
        suffix = f"?{'&'.join(params)}" if params else ""
        return self.request("GET", f"/api/v1/ns/{namespace}/~get/{path}{suffix}")

    def list_versions(self, namespace: str, path: str) -> ApiResponse:
        return self.request("GET", f"/api/v1/ns/{namespace}/~versions/{path}")

    def delete_item(
        self,
        namespace: str,
        path: str,
        *,
        preview: bool = False,
        version: int | None = None,
    ) -> ApiResponse:
        params: dict[str, str] = {"preview": "true" if preview else "false"}
        if version is not None:
            params["version"] = str(version)
        qs = urlencode(params)
        return self.request("DELETE", f"/api/v1/ns/{namespace}/~delete/{path}?{qs}")

    def navigate(self, namespace: str, path: str = "") -> ApiResponse:
        suffix = path.strip("/")
        if suffix:
            return self.request("GET", f"/api/v1/ns/{namespace}/~navigate/{suffix}")
        return self.request("GET", f"/api/v1/ns/{namespace}/~navigate/")

    def describe_item(self, namespace: str, path: str, description: str) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~describe/{path}",
            data=json.dumps({"description": description}),
            content_type="application/json",
        )

    def resolve(
        self,
        namespace: str,
        path: str,
        query: Optional[dict[str, Any]] = None,
    ) -> ApiResponse:
        qs = urlencode(query or {}, doseq=True)
        suffix = f"?{qs}" if qs else ""
        return self.request(
            "GET",
            f"/api/v1/ns/{namespace}/~resolve/{path}{suffix}",
        )

    def download_artifact(self, url: str) -> bytes:
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def list_locks(self, namespace: str) -> ApiResponse:
        return self.request("GET", f"/api/v1/ns/{namespace}/~lock/")

    def get_lock(self, namespace: str, path: str) -> ApiResponse:
        return self.request("GET", f"/api/v1/ns/{namespace}/~lock/{path}")

    def create_lock(
        self,
        namespace: str,
        path: str,
        reason: str,
        *,
        expires_at: str | None = None,
    ) -> ApiResponse:
        body: dict[str, Any] = {"reason": reason}
        if expires_at is not None:
            body["expires_at"] = expires_at
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~lock/{path}",
            data=json.dumps(body),
            content_type="application/json",
        )

    def replace_lock(
        self,
        namespace: str,
        path: str,
        reason: str,
        *,
        expires_at: str | None = None,
    ) -> ApiResponse:
        body: dict[str, Any] = {"reason": reason}
        if expires_at is not None:
            body["expires_at"] = expires_at
        return self.request(
            "PUT",
            f"/api/v1/ns/{namespace}/~lock/{path}",
            data=json.dumps(body),
            content_type="application/json",
        )

    def delete_lock(self, namespace: str, path: str) -> ApiResponse:
        return self.request("DELETE", f"/api/v1/ns/{namespace}/~lock/{path}")

    def set_tag(
        self,
        namespace: str,
        path: str,
        tag: str,
        *,
        version: int | None = None,
    ) -> ApiResponse:
        body: dict[str, Any] = {"tag": tag}
        if version is not None:
            body["version"] = version
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~tag/{path}",
            data=json.dumps(body),
            content_type="application/json",
        )

    def propagate_config(
        self,
        namespace: str,
        path: str,
        *,
        version: str = "latest",
    ) -> ApiResponse:
        qs = urlencode({"version": version}) if version != "latest" else ""
        suffix = f"?{qs}" if qs else ""
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~propagate/{path}{suffix}",
        )

    def move_item(self, namespace: str, path: str, target_path: str) -> ApiResponse:
        return self.request(
            "POST",
            f"/api/v1/ns/{namespace}/~move/{path}",
            data=json.dumps({"target_path": target_path}),
            content_type="application/json",
        )
