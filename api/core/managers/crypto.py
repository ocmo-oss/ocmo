import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

_NONCE_SIZE = 12  # 96-bit nonce for AES-256-GCM


class CryptoManager:
    """Namespace-scoped AES-256-GCM encrypt/decrypt for secret version blobs."""

    def __init__(self, namespace):
        self.namespace = namespace

    def encrypt_secret(self, plaintext: str) -> bytes:
        """Return (nonce || ciphertext || tag) for storage in SecretVersion.encrypted_data."""
        dek = self._get_or_create_dek()
        return self._encrypt_with_dek(dek, plaintext)

    def decrypt_secret(self, encrypted_data: bytes | memoryview | None) -> str | None:
        """Decrypt a secret blob; None if encrypted_data is missing or empty."""
        if not encrypted_data:
            return None
        dek = self._get_or_create_dek()
        return self._decrypt_with_dek(dek, bytes(encrypted_data))

    def _get_or_create_dek(self) -> bytes:
        """Return the plaintext DEK for this namespace, creating and persisting it if absent."""
        if self.namespace.encrypted_dek:
            return self._unwrap_dek(bytes(self.namespace.encrypted_dek))
        dek = os.urandom(32)
        self.namespace.encrypted_dek = self._wrap_dek(dek)
        self.namespace.save(update_fields=["encrypted_dek"])
        return dek

    @staticmethod
    def _master_key() -> bytes:
        """Return the 32-byte master KEK from settings, decoded from base64."""
        raw = getattr(settings, "OCMO_MASTER_KEY", None)
        if not raw:
            raise RuntimeError("OCMO_MASTER_KEY is not configured")
        key = base64.b64decode(raw)
        if len(key) != 32:
            raise RuntimeError("OCMO_MASTER_KEY must be a base64-encoded 32-byte value")
        return key

    @classmethod
    def _wrap_dek(cls, dek: bytes) -> bytes:
        """Encrypt a DEK with the master KEK; returns (nonce || ciphertext || tag)."""
        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(cls._master_key())
        ct = aesgcm.encrypt(nonce, dek, None)
        return nonce + ct

    @classmethod
    def _unwrap_dek(cls, wrapped: bytes) -> bytes:
        """Decrypt a wrapped DEK using the master KEK."""
        nonce = wrapped[:_NONCE_SIZE]
        ct = wrapped[_NONCE_SIZE:]
        aesgcm = AESGCM(cls._master_key())
        return aesgcm.decrypt(nonce, ct, None)

    @staticmethod
    def _encrypt_with_dek(dek: bytes, plaintext: str) -> bytes:
        """Return (nonce || ciphertext || tag) for plaintext using AES-256-GCM."""
        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(dek)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ct

    @staticmethod
    def _decrypt_with_dek(dek: bytes, blob: bytes) -> str:
        """Decrypt (nonce || ciphertext || tag) and return plaintext string."""
        nonce = blob[:_NONCE_SIZE]
        ct = blob[_NONCE_SIZE:]
        aesgcm = AESGCM(dek)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
