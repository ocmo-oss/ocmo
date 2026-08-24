"""Internal Pydantic schemas for parsed _webhooks config entries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class WebhookFilterSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    paths: list[str] = []


class WebhookPayloadSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    preset: str | None = None
    template: str | None = None
    headers: dict[str, str] = {}


class WebhookEntrySchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    enabled: bool
    url: str
    events: list[str]
    filter: WebhookFilterSchema | None = None
    signature_header: str = "X-OCMO-Signature"
    signature_key: str
    payload: WebhookPayloadSchema = WebhookPayloadSchema()


class WebhooksConfig(BaseModel):
    """Parsed and resolved _webhooks config ready for dispatch."""

    model_config = ConfigDict(extra="ignore")

    entries: list[WebhookEntrySchema] = []
