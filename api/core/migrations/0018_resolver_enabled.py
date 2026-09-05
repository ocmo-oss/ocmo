from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_sync_permissions_schema_valid_actions"),
    ]

    operations = [
        migrations.AddField(
            model_name="resolver",
            name="enabled",
            field=models.BooleanField(
                default=True,
                help_text="When false, resolver tokens authenticate but cannot resolve or probe permissions.",
            ),
        ),
    ]
