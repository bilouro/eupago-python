from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from eupago.exceptions import DecryptionError, SignatureError
from eupago.models.payment import PaymentStatus
from eupago.webhooks import parse_webhook


def _sign(body: bytes, secret: str) -> str:
    """eupago signs with base64(HMAC-SHA256(raw_body, secret))."""
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def _encrypt(plaintext: bytes, secret: str) -> tuple[str, str]:
    """Mirror eupago's AES-256-CBC scheme: secret IS the 32-byte key (no derivation).

    Confirmed against a real sandbox encrypted webhook.
    """
    key = secret.encode()
    assert len(key) == 32, "test secret must be 32 bytes (matches the Chave Criptográfica)"
    iv = os.urandom(16)
    padder = PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode(), base64.b64encode(iv).decode()


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
        "transaction": {
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
    body_dict = {"transaction": {"trid": 1, "status": "Paid", "identifier": "X"}}
    body_bytes = json.dumps(body_dict).encode()
    secret = "my-webhook-secret"
    signature = _sign(body_bytes, secret)

    event = parse_webhook(
        body=body_bytes,
        headers={"X-Signature": signature},
        webhook_secret=secret,
    )

    assert event.status == PaymentStatus.PAID


def test_v2_webhook_bad_signature_raises() -> None:
    body_bytes = b'{"transaction": {"trid": 1, "status": "Paid"}}'
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


def test_v2_webhook_encrypted_roundtrip() -> None:
    # 32-byte secret matching the channel's "Chave Criptográfica" length
    secret = "0123456789abcdef0123456789abcdef"
    plaintext = json.dumps(
        {
            "transaction": {
                "trid": 78901,
                "identifier": "ORD-ENC-1",
                "reference": 999888777,
                "entity": 12345,
                "method": "Mbway",
                "amount": {"value": 49.90, "currency": "EUR"},
                "status": "Paid",
            }
        }
    ).encode()
    ciphertext_b64, iv_b64 = _encrypt(plaintext, secret)
    body = json.dumps({"data": ciphertext_b64}).encode()

    event = parse_webhook(
        body=body,
        headers={
            # For encrypted webhooks eupago signs the base64 ciphertext STRING
            # (the value of "data"), not the full body.
            "X-Signature": _sign(ciphertext_b64.encode(), secret),
            "X-Initialization-Vector": iv_b64,
        },
        webhook_secret=secret,
    )

    assert event.order_id == "ORD-ENC-1"
    assert event.transaction_id == "78901"
    assert event.status == PaymentStatus.PAID
    assert str(event.amount) == "49.9"
    assert event.method == "mbway"


def test_v2_webhook_invalid_ciphertext_raises() -> None:
    secret = "0123456789abcdef0123456789abcdef"  # 32 bytes
    iv_b64 = base64.b64encode(os.urandom(16)).decode()
    # 7 bytes is not a multiple of the AES block size -> deterministic decrypt failure
    bad_ciphertext = base64.b64encode(os.urandom(7)).decode()
    body = json.dumps({"data": bad_ciphertext}).encode()

    with pytest.raises(DecryptionError):
        parse_webhook(
            body=body,
            headers={"X-Initialization-Vector": iv_b64},
            webhook_secret=secret,
        )


def test_v2_webhook_wrong_secret_length_raises() -> None:
    """The AES key must be exactly 32 bytes — the backoffice always generates that."""
    body = json.dumps({"data": base64.b64encode(os.urandom(32)).decode()}).encode()
    iv_b64 = base64.b64encode(os.urandom(16)).decode()

    with pytest.raises(DecryptionError, match="32 bytes"):
        parse_webhook(
            body=body,
            headers={"X-Initialization-Vector": iv_b64},
            webhook_secret="too-short",
        )


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("Paid", PaymentStatus.PAID),
        ("Expired", PaymentStatus.EXPIRED),
        ("Cancel", PaymentStatus.CANCELLED),
        ("Refund", PaymentStatus.REFUNDED),
        ("Error", PaymentStatus.ERROR),
        ("desconhecido", PaymentStatus.PENDING),
    ],
)
def test_v2_webhook_status_variants(raw_status: str, expected: PaymentStatus) -> None:
    body = json.dumps({"transaction": {"trid": 1, "status": raw_status}}).encode()
    event = parse_webhook(body=body)
    assert event.status == expected


def test_v2_webhook_amount_as_scalar() -> None:
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid", "amount": 12.5}}).encode()
    event = parse_webhook(body=body)
    assert str(event.amount) == "12.5"
    assert event.currency == "EUR"


def test_v2_webhook_minimal_fields() -> None:
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid"}}).encode()
    event = parse_webhook(body=body)
    assert event.transaction_id == "1"
    assert event.reference is None
    assert event.entity is None
    assert event.fee is None
    assert event.channel is None
    assert event.currency == "EUR"


def test_v2_refund_webhook_carries_original_trid() -> None:
    """eupago DOES fire a webhook on refunds (contrary to their docs).
    Live-verified shape from production 2026-05-31:

        method="RB:PT", status="REFUNDED", originalTrid=<original payment trid>

    The SDK normalises method to "refund", status to REFUNDED, and exposes the
    link back to the original payment via WebhookEvent.original_transaction_id.
    """
    body = json.dumps(
        {
            "channel": {"account": "Destrezàvolta", "name": "Destrezàvolta, Lda"},
            "transaction": {
                "reference": "70126512",
                "identifier": "PROD-MW-74685211ac",
                "method": "RB:PT",
                "amount": {"value": 1, "currency": "EUR"},
                "fees": {"value": 0, "currency": "EUR"},
                "date": "2026-05-31T18:05:00",
                "trid": "113194712",
                "originalTrid": "113193247",
                "status": "REFUNDED",
            },
        }
    ).encode()
    event = parse_webhook(body=body)
    assert event.status == PaymentStatus.REFUNDED
    assert event.method == "refund"
    assert event.transaction_id == "113194712"
    assert event.original_transaction_id == "113193247"
    assert event.order_id == "PROD-MW-74685211ac"


def test_parse_webhook_from_fixture(fixture_data) -> None:
    body = json.dumps(fixture_data("webhook_v2_paid")).encode()
    event = parse_webhook(body=body)
    assert event.order_id == "ORD-2026-001"
    assert event.transaction_id == "78901"
    assert event.status == PaymentStatus.PAID
    assert event.method == "multibanco"
    assert event.channel == "demo-channel"
    assert str(event.fee) == "0.8364"
