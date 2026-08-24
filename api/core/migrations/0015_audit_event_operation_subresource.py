# Generated manually for audit operation/subresource fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_sync_permissions_webhooks_builtin_schemas"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="operation",
            field=models.CharField(blank=True, db_index=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="subresource",
            field=models.CharField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="subresource_type",
            field=models.CharField(blank=True, db_index=True, max_length=128, null=True),
        ),
    ]
