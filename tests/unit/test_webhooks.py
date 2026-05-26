from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from eupago.exceptions import SignatureError
from eupago.models.payment import PaymentStatus
from eupago.webhooks import parse_webhook


def test_parse_v1_webhook() -> None:
    params = {
        "valor": "49.90",
        "identificador": "ORD-001",
        "transacao": "12345",
        "referencia": "999888777",
        "entidade": "12345",
        "mp": "MW:PT",
        "data": "2026-05-26:14:30",
        "canal": "main",
        "comissao": "0.35",
    }

    event = parse_webhook(query_params=params)

    assert event.order_id == "ORD-001"
    assert event.transaction_id == "12345"
    assert event.reference == "999888777"
    assert event.entity == "12345"
    assert str(event.amount) == "49.90"
    assert event.method == "mbway"
    assert event.channel == "main"
    assert str(event.fee) == "0.35"


def test_parse_v2_webhook() -> None:
    body = {
        "transactions": {
            "entity": 12345,
            "reference": 999888777,
            "identifier": "ORD-2026-001",
            "method": "Mbway",
            "amount": {"value": 49.90, "currency": "EUR"},
            "fees": {"value": 0.35, "currency": "EUR"},
            "date": "2026-05-26T14:30:00Z",
            "trid": 78901,
            "status": "Paid",
        },
        "channel": {"name": "main-channel"},
    }

    event = parse_webhook(body=json.dumps(body).encode())

    assert event.order_id == "ORD-2026-001"
    assert event.transaction_id == "78901"
    assert event.status == PaymentStatus.PAID
    assert event.method == "mbway"
    assert str(event.amount) == "49.9"
    assert event.currency == "EUR"
    assert event.channel == "main-channel"
    assert str(event.fee) == "0.35"


def test_v2_webhook_signature_verification() -> None:
    body_dict = {"transactions": {"trid": 1, "status": "Paid", "identifier": "X"}}
    body_bytes = json.dumps(body_dict).encode()
    secret = "my-webhook-secret"
    signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()

    event = parse_webhook(
        body=body_bytes,
        headers={"X-Signature": signature},
        webhook_secret=secret,
    )

    assert event.status == PaymentStatus.PAID


def test_v2_webhook_bad_signature_raises() -> None:
    body_bytes = b'{"transactions": {"trid": 1, "status": "Paid"}}'
    with pytest.raises(SignatureError, match="signature verification failed"):
        parse_webhook(
            body=body_bytes,
            headers={"X-Signature": "bad-signature"},
            webhook_secret="my-secret",
        )


def test_parse_webhook_requires_body_or_params() -> None:
    from eupago.exceptions import WebhookError

    with pytest.raises(WebhookError, match="body or query_params"):
        parse_webhook()
