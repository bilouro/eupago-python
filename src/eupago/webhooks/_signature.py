from __future__ import annotations

import base64
import hashlib
import hmac

from eupago.exceptions import DecryptionError, SignatureError


def verify_signature(payload: bytes, signature: str, secret: str) -> None:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("Webhook signature verification failed")


def decrypt_payload(encrypted_data: str, secret: str, iv_b64: str) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers import (
            Cipher,
            algorithms,
            modes,
        )
        from cryptography.hazmat.primitives.padding import PKCS7
    except ImportError:
        raise DecryptionError(
            "Encrypted webhooks require the 'cryptography' package: pip install eupago[crypto]"
        ) from None

    try:
        iv = base64.b64decode(iv_b64)
        data = base64.b64decode(encrypted_data)
        key = hashlib.sha256(secret.encode()).digest()

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded: bytes = decryptor.update(data) + decryptor.finalize()

        unpadder = PKCS7(128).unpadder()
        result: bytes = unpadder.update(padded) + unpadder.finalize()
        return result
    except Exception as exc:
        if isinstance(exc, DecryptionError):
            raise
        raise DecryptionError(f"Failed to decrypt webhook payload: {exc}") from exc
