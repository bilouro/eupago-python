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


# Live-verified sandbox response shape (May 2026):
#   201 {"transactionStatus": "Success", "refundId": "2788", "status": "Reembolsado"}
_LIVE_RESPONSE = {"transactionStatus": "Success", "refundId": "2788", "status": "Reembolsado"}


@respx.mock
def test_refund_success(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-abc").mock(
        return_value=Response(201, json=_LIVE_RESPONSE)
    )

    result = client.refunds.refund(
        transaction_id="txn-abc",
        amount=Decimal("49.90"),
        reason="customer request",
    )

    # eupago expects {amount, reason} — NOT {value, currency, motivo} (the
    # earlier SDK shape returned AMOUNT_MISSING from production).
    body = json.loads(route.calls[0].request.content)
    assert body == {"amount": 49.90, "reason": "customer request"}
    assert result.status == PaymentStatus.REFUNDED
    assert result.transaction_id == "txn-abc"
    assert result.amount == Decimal("49.90")
    assert result.method == "refund"
    assert result.raw_response["refundId"] == "2788"


@respx.mock
def test_refund_sends_oauth_bearer(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-001").mock(
        return_value=Response(201, json=_LIVE_RESPONSE)
    )

    client.refunds.refund(transaction_id="txn-001", amount=Decimal("1.00"))

    assert route.calls[0].request.headers["authorization"] == "Bearer oauth-token"


@respx.mock
def test_refund_partial_no_reason_omits_reason(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-002").mock(
        return_value=Response(201, json=_LIVE_RESPONSE)
    )

    client.refunds.refund(transaction_id="txn-002", amount=Decimal("10.00"))

    body = json.loads(route.calls[0].request.content)
    assert body == {"amount": 10.0}


@respx.mock
def test_refund_with_iban_bic(client: EupagoClient) -> None:
    _mock_oauth_token()
    route = respx.post(f"{REFUND_URL}/txn-003").mock(
        return_value=Response(201, json=_LIVE_RESPONSE)
    )

    client.refunds.refund(
        transaction_id="txn-003",
        amount=Decimal("5.50"),
        reason="manual",
        iban="PT50000000000000000000000",
        bic="TESTBIC",
    )

    body = json.loads(route.calls[0].request.content)
    assert body == {
        "amount": 5.5,
        "reason": "manual",
        "iban": "PT50000000000000000000000",
        "bic": "TESTBIC",
    }


@respx.mock
def test_refund_failure_sets_error_status(client: EupagoClient) -> None:
    _mock_oauth_token()
    respx.post(f"{REFUND_URL}/txn-bad").mock(
        return_value=Response(200, json={"transactionStatus": "Rejected"})
    )

    result = client.refunds.refund(transaction_id="txn-bad", amount=Decimal("1.00"))

    assert result.status == PaymentStatus.ERROR


def test_refund_rejects_zero_or_negative(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="positive"):
        client.refunds.refund(transaction_id="txn-x", amount=Decimal("0"))
    with pytest.raises(ValidationError, match="positive"):
        client.refunds.refund(transaction_id="txn-x", amount=Decimal("-1"))


def test_refund_without_oauth_credentials_raises() -> None:
    """Refunds require management auth — without it the SDK must fail loud."""
    from eupago import AuthenticationError

    client = EupagoClient(api_key="k", sandbox=True)  # no client_id/secret/bearer
    with pytest.raises(AuthenticationError, match="Management API authentication"):
        client.refunds.refund(transaction_id="txn", amount=Decimal("1.00"))


@respx.mock
def test_refund_with_management_bearer_bypasses_oauth() -> None:
    """A caller can inject a pre-obtained Bearer (e.g. from the backoffice login)
    via ``management_bearer`` instead of going through OAuth.
    """
    bo_client = EupagoClient(
        api_key="k",
        management_bearer="bo-session-bearer",
        sandbox=True,
    )
    route = respx.post(f"{REFUND_URL}/txn-bo").mock(return_value=Response(201, json=_LIVE_RESPONSE))

    result = bo_client.refunds.refund(transaction_id="txn-bo", amount=Decimal("1.00"))

    assert route.calls[0].request.headers["authorization"] == "Bearer bo-session-bearer"
    assert result.status == PaymentStatus.REFUNDED


@respx.mock
@pytest.mark.asyncio
async def test_refund_async_success(client: EupagoClient) -> None:
    _mock_oauth_token()
    respx.post(f"{REFUND_URL}/txn-async").mock(return_value=Response(201, json=_LIVE_RESPONSE))

    result = await client.refunds.refund_async(
        transaction_id="txn-async",
        amount=Decimal("5.00"),
    )

    assert result.status == PaymentStatus.REFUNDED
    await client.aclose()
