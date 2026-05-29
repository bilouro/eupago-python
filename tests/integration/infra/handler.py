"""Lambda webhook receiver — SDK integration-test infrastructure.

Captures incoming eupago webhooks into DynamoDB. The raw body and headers are
**always** stored verbatim (so the SDK can verify signatures offline against the
exact bytes). When the channel encrypts and ``WEBHOOK_SECRET`` is configured the
Lambda also decrypts to extract the eupago ``identifier``, so the item is keyed
by the merchant's ``order_id`` whether or not encryption is on.

Env vars:
- ``WEBHOOK_TABLE`` (required) — DynamoDB table name.
- ``WEBHOOK_SECRET`` (optional) — the channel's Chave Criptográfica. Required
  to extract ``order_id`` from encrypted captures.
- ``WEBHOOK_TTL_DAYS`` (optional, default 7) — TTL for captured items.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any

import boto3

_TABLE_NAME = os.environ["WEBHOOK_TABLE"]
_TTL_DAYS = int(os.environ.get("WEBHOOK_TTL_DAYS", "7"))
_SECRET = os.environ.get("WEBHOOK_SECRET")
_table = boto3.resource("dynamodb").Table(_TABLE_NAME)


def _raw_body(event: dict[str, Any]) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8", "replace")
    return body


def _decrypt(ciphertext_b64: str, iv_b64: str, secret: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7

    key = secret.encode()
    iv = base64.b64decode(iv_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()  # type: ignore[no-any-return]


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = _raw_body(event)
    encrypted = "x-initialization-vector" in headers or '"data"' in body

    payload_to_parse = body
    if encrypted and _SECRET:
        try:
            outer = json.loads(body)
            payload_to_parse = _decrypt(
                outer["data"], headers["x-initialization-vector"], _SECRET
            ).decode("utf-8", "replace")
        except Exception:  # noqa: S110 - capture must never 500; raw is preserved
            pass  # raw_body is still stored, so offline analysis is possible

    order_id: str | None = None
    reference: str | None = None
    status: str | None = None
    try:
        data = json.loads(payload_to_parse)
        if isinstance(data, dict):
            tx = data.get("transaction") or data.get("transactions") or data
            order_id = tx.get("identifier")
            reference = str(tx["reference"]) if tx.get("reference") is not None else None
            status = tx.get("status")
    except ValueError:
        pass

    now = int(time.time())
    item: dict[str, Any] = {
        "order_id": order_id or f"raw-{uuid.uuid4().hex}",
        "received_at": now,
        "ttl": now + _TTL_DAYS * 86400,
        "raw_body": body,
        "headers": json.dumps(headers),
        "encrypted": encrypted,
    }
    for key, value in (
        ("x_signature", headers.get("x-signature")),
        ("x_initialization_vector", headers.get("x-initialization-vector")),
        ("reference", reference),
        ("status", status),
    ):
        if value is not None:
            item[key] = value

    _table.put_item(Item=item)
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
