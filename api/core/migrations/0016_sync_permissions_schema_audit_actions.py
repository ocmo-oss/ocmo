"""Sync _permissions.schema to include :audit policy actions."""

from __future__ import annotations

from django.db import migrations


def sync_permissions_schema_audit_actions(apps, schema_editor):
    from core.models import Namespace
    from core.utils.namespace_special_configs import sync_permissions_webhooks_schema_configs

    for namespace in Namespace.objects.all().iterator():
        sync_permissions_webhooks_schema_configs(namespace)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_audit_event_operation_subresource"),
    ]

    operations = [
        migrations.RunPython(
            sync_permissions_schema_audit_actions,
            migrations.RunPython.noop,
        ),
    ]
