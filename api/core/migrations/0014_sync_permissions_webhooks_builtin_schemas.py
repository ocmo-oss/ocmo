"""Sync packaged _permissions.schema and _webhooks.schema into every namespace."""

from __future__ import annotations

from django.db import migrations


def sync_permissions_webhooks_schemas(apps, schema_editor):
    from core.models import Namespace
    from core.utils.namespace_special_configs import sync_permissions_webhooks_schema_configs

    for namespace in Namespace.objects.all().iterator():
        sync_permissions_webhooks_schema_configs(namespace)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_audit_event_object_id"),
    ]

    operations = [
        migrations.RunPython(
            sync_permissions_webhooks_schemas,
            migrations.RunPython.noop,
        ),
    ]
