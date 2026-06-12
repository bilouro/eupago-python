from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/applepay/create"
_FAKE_TOKEN = '{"paymentData": {"version": "...", "data": "..."}}'


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
                "transactionID": "txn-ap-001",
                "reference": "306500",
            },
        )
    )

    result = client.apple_pay.create_payment(
        order_id="ORD-AP-001",
        amount=Decimal("49.90"),
        apple_pay_token=_FAKE_TOKEN,
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["amount"] == {"value": 49.90, "currency": "EUR"}
    assert body["payment"]["applePayToken"] == _FAKE_TOKEN
    assert body["payment"]["identifier"] == "ORD-AP-001"

    assert result.transaction_id == "txn-ap-001"
    assert result.reference == "306500"
    assert result.status == PaymentStatus.PENDING
    assert result.method == "apple_pay"


@respx.mock
def test_create_payment_sends_header_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"transactionStatus": "Success"})
    )

    client.apple_pay.create_payment(
        order_id="ORD-AP-002",
        amount=Decimal("10.00"),
        apple_pay_token=_FAKE_TOKEN,
    )

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_hosted_flow_no_token(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "transactionID": "txn-hosted-ap",
                "reference": "306501",
                "redirectUrl": "https://sandbox.eupago.pt/api/extern/applepay/form/txn-hosted-ap",
            },
        )
    )

    result = client.apple_pay.create_payment(
        order_id="ORD-AP-HOSTED",
        amount=Decimal("12.34"),
    )

    body = json.loads(route.calls[0].request.content)
    assert "applePayToken" not in body["payment"]
    assert body["payment"]["identifier"] == "ORD-AP-HOSTED"
    assert result.payment_url == (
        "https://sandbox.eupago.pt/api/extern/applepay/form/txn-hosted-ap"
    )
    assert result.status == PaymentStatus.PENDING


def test_create_payment_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.apple_pay.create_payment(
            order_id="ORD-AP-MAX",
            amount=Decimal("100000"),
            apple_pay_token=_FAKE_TOKEN,
        )


@respx.mock
def test_create_payment_rejected_returns_error(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(200, json={"transactionStatus": "Rejected"}))

    result = client.apple_pay.create_payment(
        order_id="ORD-AP-REJ",
        amount=Decimal("10.00"),
        apple_pay_token=_FAKE_TOKEN,
    )
    assert result.status == PaymentStatus.ERROR


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-async-ap"}
        )
    )

    result = await client.apple_pay.create_payment_async(
        order_id="ORD-AP-ASYNC",
        amount=Decimal("15.00"),
        apple_pay_token=_FAKE_TOKEN,
    )

    assert result.transaction_id == "txn-async-ap"
    assert result.method == "apple_pay"
    await client.aclose()
