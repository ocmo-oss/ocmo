"""Encrypt resolver tokens at rest and add HMAC lookup columns."""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.db import migrations, models


def _signing_key() -> bytes:
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def _fingerprint(plaintext: str) -> str:
    return hmac.new(_signing_key(), plaintext.encode("utf-8"), hashlib.sha256).hexdigest()


def _encrypt(plaintext: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_signing_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def encrypt_existing_tokens(apps, schema_editor):
    Resolver = apps.get_model("core", "Resolver")
    for resolver in Resolver.objects.all().iterator():
        changed = False
        for slot, token_field, lookup_field in (
            (1, "token1", "token1_lookup"),
            (2, "token2", "token2_lookup"),
        ):
            plaintext = getattr(resolver, token_field)
            if not plaintext:
                continue
            # Skip values already encrypted (base64 blobs longer than raw tokens).
            if len(plaintext) > 80:
                continue
            setattr(resolver, lookup_field, _fingerprint(plaintext))
            setattr(resolver, token_field, _encrypt(plaintext))
            changed = True
        if changed:
            resolver.save(update_fields=["token1", "token2", "token1_lookup", "token2_lookup"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_tree_lock"),
    ]

    operations = [
        migrations.AddField(
            model_name="resolver",
            name="token1_lookup",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="resolver",
            name="token2_lookup",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="resolver",
            name="token1",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="resolver",
            name="token2",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(encrypt_existing_tokens, migrations.RunPython.noop),
    ]
