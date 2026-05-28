from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError
from eupago.models.customer import Customer

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/applepay/create"


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_payment_success(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            200,
            json={
                "transactionID": "txn-apple-001",
                "estado": 0,
                "redirectUrl": "https://pay.eupago.pt/apple/abc",
            },
        )
    )

    result = client.apple_pay.create_payment(
        order_id="ORD-AP-001",
        amount=Decimal("29.99"),
    )

    assert result.transaction_id == "txn-apple-001"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url == "https://pay.eupago.pt/apple/abc"
    assert result.method == "apple_pay"
    assert result.amount == Decimal("29.99")


@respx.mock
def test_create_payment_sends_api_key_header(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "txn-1"})
    )

    client.apple_pay.create_payment(order_id="ORD-AP-002", amount=Decimal("10.00"))

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_with_urls(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "txn-2"})
    )

    client.apple_pay.create_payment(
        order_id="ORD-AP-003",
        amount=Decimal("50.00"),
        success_url="https://example.com/ok",
        error_url="https://example.com/fail",
        callback_url="https://example.com/webhook",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["successUrl"] == "https://example.com/ok"
    assert body["payment"]["failUrl"] == "https://example.com/fail"
    assert body["payment"]["adminCallback"] == "https://example.com/webhook"


@respx.mock
def test_create_payment_with_customer(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "txn-3"})
    )

    customer = Customer(email="test@example.com", notify=True)
    client.apple_pay.create_payment(
        order_id="ORD-AP-004",
        amount=Decimal("15.00"),
        customer=customer,
    )

    body = json.loads(route.calls[0].request.content)
    assert body["customer"]["email"] == "test@example.com"


def test_create_payment_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.apple_pay.create_payment(order_id="ORD-AP-005", amount=Decimal("0"))


def test_create_payment_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.apple_pay.create_payment(order_id="ORD-AP-006", amount=Decimal("100000"))


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"transactionID": "txn-async-ap", "estado": 0})
    )

    result = await client.apple_pay.create_payment_async(
        order_id="ORD-AP-ASYNC",
        amount=Decimal("20.00"),
    )

    assert result.transaction_id == "txn-async-ap"
    assert result.method == "apple_pay"
    await client.aclose()
