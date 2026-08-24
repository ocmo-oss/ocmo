"""Encrypt resolver tokens at rest using a key derived from Django SECRET_KEY."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.db.models import Q

from ..models import Resolver

_NONCE_SIZE = 12


class ResolverTokenManager:
    """Store, reveal, and authenticate a single resolver API token."""

    def __init__(
        self,
        *,
        plaintext: str | None = None,
        encrypted: str | None = None,
    ) -> None:
        if (plaintext is None) == (encrypted is None):
            raise ValueError("Exactly one of plaintext or encrypted must be provided")
        self._plaintext = plaintext
        self._encrypted = encrypted

    @staticmethod
    def _signing_key() -> bytes:
        return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()

    @staticmethod
    def _decrypt_encrypted(blob_b64: str) -> str:
        blob = base64.b64decode(blob_b64.encode("ascii"))
        nonce, ct = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
        return AESGCM(ResolverTokenManager._signing_key()).decrypt(nonce, ct, None).decode("utf-8")

    @staticmethod
    def _encrypt_plaintext(plaintext: str) -> str:
        nonce = os.urandom(_NONCE_SIZE)
        ct = AESGCM(ResolverTokenManager._signing_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("ascii")

    @property
    def plaintext(self) -> str:
        if self._plaintext is None:
            self._plaintext = self._decrypt_encrypted(self._encrypted)  # type: ignore[arg-type]
        return self._plaintext

    @property
    def encrypted(self) -> str:
        if self._encrypted is None:
            self._encrypted = self._encrypt_plaintext(self._plaintext)  # type: ignore[arg-type]
        return self._encrypted

    @classmethod
    def from_encrypted(cls, blob_b64: str) -> ResolverTokenManager | None:
        """Build from ciphertext; return None when decryption fails."""
        mgr = cls(encrypted=blob_b64)
        try:
            mgr.plaintext
        except Exception:  # noqa: BLE001
            return None
        return mgr

    @classmethod
    def from_resolver(cls, resolver: Resolver, slot: int) -> ResolverTokenManager | None:
        """Reveal the plaintext token stored on a resolver slot, if present."""
        blob = resolver.token1 if slot == 1 else resolver.token2
        if not blob:
            return None
        return cls.from_encrypted(blob)

    def fingerprint(self) -> str:
        """Deterministic HMAC used for indexed DB lookup."""
        return hmac.new(
            self._signing_key(),
            self.plaintext.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def assign_to(self, resolver: Resolver, slot: int) -> None:
        """Encrypt and persist this token on the given resolver slot."""
        lookup = self.fingerprint()
        if slot == 1:
            resolver.token1 = self.encrypted
            resolver.token1_lookup = lookup
        elif slot == 2:
            resolver.token2 = self.encrypted
            resolver.token2_lookup = lookup
        else:
            raise ValueError("slot must be 1 or 2")

    def authenticate(self) -> tuple[Resolver, int] | None:
        """Locate a resolver whose stored token matches this plaintext."""
        lookup = self.fingerprint()
        try:
            resolver = Resolver.objects.get(Q(token1_lookup=lookup) | Q(token2_lookup=lookup))
        except Resolver.DoesNotExist:
            return None
        except Resolver.MultipleObjectsReturned:
            # Clonning tokens is not allowed, so we should not have multiple resolvers with the same token
            return None

        if hmac.compare_digest(resolver.token1_lookup or "", lookup):
            return resolver, 1
        if hmac.compare_digest(resolver.token2_lookup or "", lookup):
            return resolver, 2
        return None
