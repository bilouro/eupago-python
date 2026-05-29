from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from eupago import EupagoClient, PaymentStatus, SignatureError
from eupago.services.mbway import MBWayService
from eupago.webhooks import Webhooks


def test_client_creates_with_api_key() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    assert isinstance(client.mbway, MBWayService)
    client.close()


def test_client_sandbox_url() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    assert "sandbox" in client._transport._base_url
    client.close()


def test_client_production_url() -> None:
    client = EupagoClient(api_key="test-key", sandbox=False)
    assert "clientes" in client._transport._base_url
    client.close()


def test_client_lazy_service_caching() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    mbway1 = client.mbway
    mbway2 = client.mbway
    assert mbway1 is mbway2
    client.close()


def test_client_context_manager() -> None:
    with EupagoClient(api_key="test-key", sandbox=True) as client:
        assert isinstance(client.mbway, MBWayService)


def _b64_hmac(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_client_webhooks_uses_configured_secret() -> None:
    secret = "channel-secret"
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid", "identifier": "X"}}).encode()
    client = EupagoClient(api_key="k", sandbox=True, webhook_secret=secret)
    assert isinstance(client.webhooks, Webhooks)

    event = client.webhooks.parse(body=body, headers={"X-Signature": _b64_hmac(body, secret)})
    assert event.status == PaymentStatus.PAID


def test_client_webhooks_override_secret_per_call() -> None:
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid", "identifier": "X"}}).encode()
    client = EupagoClient(api_key="k", sandbox=True, webhook_secret="default-secret")

    # The signature was built with "override-secret"; the configured default would fail.
    event = client.webhooks.parse(
        body=body,
        headers={"X-Signature": _b64_hmac(body, "override-secret")},
        webhook_secret="override-secret",
    )
    assert event.status == PaymentStatus.PAID


def test_client_webhooks_secret_mismatch_raises() -> None:
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid"}}).encode()
    client = EupagoClient(api_key="k", sandbox=True, webhook_secret="wrong-secret")

    with pytest.raises(SignatureError):
        client.webhooks.parse(body=body, headers={"X-Signature": _b64_hmac(body, "right-secret")})


def test_client_webhooks_no_secret_cleartext() -> None:
    """Without a secret + no signature header, cleartext payloads still parse."""
    body = json.dumps({"transaction": {"trid": 1, "status": "Paid", "identifier": "X"}}).encode()
    client = EupagoClient(api_key="k", sandbox=True)

    event = client.webhooks.parse(body=body)
    assert event.status == PaymentStatus.PAID
    assert event.order_id == "X"
