from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/googlepay/create"
_FAKE_TOKEN = '{"paymentMethodData": {"tokenizationData": {"token": "..."}}}'


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_payment_success(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "transactionID": "txn-gp-001",
                "reference": "306600",
            },
        )
    )

    result = client.google_pay.create_payment(
        order_id="ORD-GP-001",
        amount=Decimal("49.90"),
        google_pay_token=_FAKE_TOKEN,
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["amount"] == {"value": 49.90, "currency": "EUR"}
    assert body["payment"]["googlePayToken"] == _FAKE_TOKEN

    assert result.transaction_id == "txn-gp-001"
    assert result.status == PaymentStatus.PENDING
    assert result.method == "google_pay"


@respx.mock
def test_create_payment_sends_header_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"transactionStatus": "Success"})
    )

    client.google_pay.create_payment(
        order_id="ORD-GP-002",
        amount=Decimal("10.00"),
        google_pay_token=_FAKE_TOKEN,
    )

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


def test_create_payment_requires_token(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="google_pay_token is required"):
        client.google_pay.create_payment(
            order_id="ORD-GP-NOTOK",
            amount=Decimal("10.00"),
            google_pay_token="",
        )


@respx.mock
def test_create_payment_rejected_returns_error(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(200, json={"transactionStatus": "Rejected"}))

    result = client.google_pay.create_payment(
        order_id="ORD-GP-REJ",
        amount=Decimal("10.00"),
        google_pay_token=_FAKE_TOKEN,
    )
    assert result.status == PaymentStatus.ERROR


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-async-gp"}
        )
    )

    result = await client.google_pay.create_payment_async(
        order_id="ORD-GP-ASYNC",
        amount=Decimal("15.00"),
        google_pay_token=_FAKE_TOKEN,
    )

    assert result.transaction_id == "txn-async-gp"
    assert result.method == "google_pay"
    await client.aclose()
