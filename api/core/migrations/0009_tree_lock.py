# Generated manually for TreeLock model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_namespace_tags_dek_secret_global_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="TreeLock",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("path", models.CharField(max_length=4096)),
                ("reason", models.TextField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "locked_by",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tree_locks",
                        to="core.namespace",
                    ),
                ),
            ],
            options={
                "ordering": ["path"],
                "indexes": [
                    models.Index(
                        fields=["namespace", "path"],
                        name="core_treel_namespace_path_idx",
                    ),
                    models.Index(
                        fields=["namespace", "expires_at"],
                        name="core_treel_namespace_expires_idx",
                    ),
                ],
                "unique_together": {("namespace", "path")},
            },
        ),
    ]
