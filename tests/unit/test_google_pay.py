from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError
from eupago.models.customer import Customer

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/googlepay/create"


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_payment_success(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionID": "txn-google-001",
                "estado": 0,
                "redirectUrl": "https://pay.eupago.pt/google/xyz",
            },
        )
    )

    result = client.google_pay.create_payment(
        order_id="ORD-GP-001",
        amount=Decimal("35.00"),
    )

    assert result.transaction_id == "txn-google-001"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url == "https://pay.eupago.pt/google/xyz"
    assert result.method == "google_pay"


@respx.mock
def test_create_payment_sends_api_key_header(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"estado": 0, "transactionID": "txn-1"})
    )

    client.google_pay.create_payment(order_id="ORD-GP-002", amount=Decimal("10.00"))

    assert route.calls[0].request.headers["apikey"] == "test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_with_urls_and_customer(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"estado": 0, "transactionID": "txn-2"})
    )

    customer = Customer(email="buyer@example.com", phone_number="351#912345678")
    client.google_pay.create_payment(
        order_id="ORD-GP-003",
        amount=Decimal("75.00"),
        customer=customer,
        success_url="https://shop.com/ok",
        error_url="https://shop.com/fail",
        callback_url="https://shop.com/webhook",
        description="Test purchase",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["successUrl"] == "https://shop.com/ok"
    assert body["payment"]["failUrl"] == "https://shop.com/fail"
    assert body["payment"]["adminCallback"] == "https://shop.com/webhook"
    assert body["payment"]["description"] == "Test purchase"
    assert body["customer"]["email"] == "buyer@example.com"
    assert body["customer"]["phone"] == "351#912345678"


def test_create_payment_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.google_pay.create_payment(order_id="ORD-GP-004", amount=Decimal("0"))


@respx.mock
def test_create_payment_error_status(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"estado": -1, "resposta": "Error"})
    )

    result = client.google_pay.create_payment(
        order_id="ORD-GP-005",
        amount=Decimal("10.00"),
    )

    assert result.status == PaymentStatus.ERROR


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"transactionID": "txn-async-gp", "estado": 0})
    )

    result = await client.google_pay.create_payment_async(
        order_id="ORD-GP-ASYNC",
        amount=Decimal("45.00"),
    )

    assert result.transaction_id == "txn-async-gp"
    assert result.method == "google_pay"
    await client.aclose()
