from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError

SANDBOX = "https://sandbox.eupago.pt"
TOKEN_URL = f"{SANDBOX}/api/auth/token"
REFUND_URL = f"{SANDBOX}/api/management/v1.02/refund"


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(
        api_key="test-0000-0000-0000-0000",
        client_id="cid",
        client_secret="csecret",
        sandbox=True,
    )


def _mock_oauth_token() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={"access_token": "oauth-token", "expires_in": 3600})
    )


@respx.mock
def test_refund_success(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-abc").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    result = client.refunds.refund(
        transaction_id="txn-abc",
        value=Decimal("49.90"),
        reason="customer request",
    )

    body = json.loads(route.calls[0].request.content)
    assert body == {"value": 49.90, "currency": "EUR", "motivo": "customer request"}
    assert result.status == PaymentStatus.REFUNDED
    assert result.transaction_id == "txn-abc"
    assert result.amount == Decimal("49.90")
    assert result.method == "refund"


@respx.mock
def test_refund_sends_oauth_bearer(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-001").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    client.refunds.refund(transaction_id="txn-001", value=Decimal("1.00"))

    assert route.calls[0].request.headers["authorization"] == "Bearer oauth-token"


@respx.mock
def test_refund_partial_no_reason_omits_motivo(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-002").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    client.refunds.refund(transaction_id="txn-002", value=Decimal("10.00"))

    body = json.loads(route.calls[0].request.content)
    assert "motivo" not in body
    assert body == {"value": 10.0, "currency": "EUR"}


@respx.mock
def test_refund_failure_sets_error_status(client: EupagoClient) -> None:
    _mock_oauth_token()
    respx.post(f"{REFUND_URL}/txn-bad").mock(
        return_value=Response(200, json={"transactionStatus": "Rejected"})
    )

    result = client.refunds.refund(transaction_id="txn-bad", value=Decimal("1.00"))

    assert result.status == PaymentStatus.ERROR


def test_refund_rejects_zero_or_negative(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="positive"):
        client.refunds.refund(transaction_id="txn-x", value=Decimal("0"))
    with pytest.raises(ValidationError, match="positive"):
        client.refunds.refund(transaction_id="txn-x", value=Decimal("-1"))


def test_refund_without_oauth_credentials_raises() -> None:
    """Refunds require OAuth — without client_id/client_secret it must fail loud."""
    from eupago import AuthenticationError

    client = EupagoClient(api_key="k", sandbox=True)  # no client_id/secret
    with pytest.raises(AuthenticationError, match="OAuth credentials"):
        client.refunds.refund(transaction_id="txn", value=Decimal("1.00"))


@respx.mock
@pytest.mark.asyncio
async def test_refund_async_success(client: EupagoClient) -> None:
    _mock_oauth_token()
    respx.post(f"{REFUND_URL}/txn-async").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    result = await client.refunds.refund_async(
        transaction_id="txn-async",
        value=Decimal("5.00"),
    )

    assert result.status == PaymentStatus.REFUNDED
    await client.aclose()
