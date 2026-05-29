"""Lambda webhook receiver — SDK integration-test infrastructure.

Captures the *raw* body and headers of incoming eupago webhooks into DynamoDB so
an integration test can fetch them by ``order_id`` and validate the SDK's
``parse_webhook``. This is TEST infra: it stores payloads, it runs no business
logic and decrypts nothing (the offline test reverse-engineers/validates from
the captured raw bytes).

No third-party dependencies — ``boto3`` ships with the Lambda Python runtime.
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
_table = boto3.resource("dynamodb").Table(_TABLE_NAME)


def _raw_body(event: dict[str, Any]) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8", "replace")
    return body


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = _raw_body(event)

    order_id: str | None = None
    reference: str | None = None
    status: str | None = None
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            # eupago v2.0 wraps fields in "transaction" (singular); keep
            # "transactions" as a fallback in case the format changes.
            tx = data.get("transaction") or data.get("transactions") or data
            order_id = tx.get("identifier")
            reference = str(tx["reference"]) if tx.get("reference") is not None else None
            status = tx.get("status")
    except ValueError:
        pass  # encrypted or non-JSON body — still captured raw below

    now = int(time.time())
    item: dict[str, Any] = {
        "order_id": order_id or f"raw-{uuid.uuid4().hex}",
        "received_at": now,
        "ttl": now + _TTL_DAYS * 86400,
        "raw_body": body,
        "headers": json.dumps(headers),
        "encrypted": ("x-initialization-vector" in headers) or ('"data"' in body),
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
