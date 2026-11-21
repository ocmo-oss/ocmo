import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_resolver_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="namespace",
            name="change_requests_auto_reject_on_new_version",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="namespace",
            name="change_requests_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="namespace",
            name="change_requests_max_open_per_user_per_resource",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="namespace",
            name="change_requests_required_approvals",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="namespace",
            name="change_requests_reset_approvals_on_change",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="ChangeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField(editable=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "open"),
                            ("rejected", "rejected"),
                            ("withdrawn", "withdrawn"),
                            ("applied", "applied"),
                        ],
                        db_index=True,
                        default="open",
                        max_length=16,
                    ),
                ),
                ("base_version", models.PositiveIntegerField()),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                ("description", models.TextField(blank=True, default="", max_length=4096)),
                ("content", models.TextField(blank=True, default="")),
                ("content_encrypted", models.BinaryField(blank=True, null=True)),
                ("created_by", models.CharField(max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("applied_version", models.PositiveIntegerField(blank=True, null=True)),
                ("applied_by", models.CharField(blank=True, max_length=512, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_reason", models.TextField(blank=True, default="", max_length=4096)),
                ("rejected_by", models.CharField(blank=True, max_length=512, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                (
                    "tree_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="change_requests",
                        to="core.treeitem",
                    ),
                ),
            ],
            options={
                "ordering": ["tree_item", "number"],
            },
        ),
        migrations.CreateModel(
            name="ChangeRequestApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("approver", models.CharField(max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "change_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="approvals",
                        to="core.changerequest",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChangeRequestComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("author", models.CharField(max_length=512)),
                ("body", models.TextField(max_length=8192)),
                ("anchor", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "change_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="core.changerequest",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="changerequest",
            index=models.Index(fields=["tree_item", "status"], name="core_change_tree_it_b8f2c1_idx"),
        ),
        migrations.AddIndex(
            model_name="changerequest",
            index=models.Index(fields=["created_by", "tree_item", "status"], name="core_change_created_4a91e0_idx"),
        ),
        migrations.AddConstraint(
            model_name="changerequest",
            constraint=models.UniqueConstraint(
                fields=("tree_item", "number"),
                name="core_changerequest_item_number_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="changerequestapproval",
            constraint=models.UniqueConstraint(
                fields=("change_request", "approver"),
                name="core_changerequestapproval_unique_approver",
            ),
        ),
        migrations.AddIndex(
            model_name="changerequestcomment",
            index=models.Index(fields=["change_request", "created_at"], name="core_change_change__f3e8a2_idx"),
        ),
    ]
