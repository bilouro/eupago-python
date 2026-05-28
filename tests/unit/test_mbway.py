from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError
from eupago.models.customer import Customer


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_payment_success(client: EupagoClient) -> None:
    respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/create").mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "transactionID": "txn-abc-123",
                "reference": "306188",
            },
        )
    )

    result = client.mbway.create_payment(
        order_id="ORD-001",
        amount=Decimal("49.90"),
        phone_number="912345678",
    )

    assert result.transaction_id == "txn-abc-123"
    assert result.reference == "306188"
    assert result.status == PaymentStatus.PENDING
    assert result.amount == Decimal("49.90")
    assert result.order_id == "ORD-001"
    assert result.method == "mbway"


@respx.mock
def test_create_payment_request_body(client: EupagoClient) -> None:
    route = respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/create").mock(
        return_value=Response(201, json={"transactionStatus": "Success", "transactionID": "t"})
    )

    client.mbway.create_payment(
        order_id="ORD-BODY",
        amount=Decimal("10.00"),
        phone_number="912345678",
    )

    payload = json.loads(route.calls[0].request.content)
    assert payload["payment"]["customerPhone"] == "912345678"
    assert payload["payment"]["amount"] == {"value": 10.0, "currency": "EUR"}
    assert payload["payment"]["identifier"] == "ORD-BODY"


@respx.mock
def test_create_payment_with_customer(client: EupagoClient) -> None:
    route = respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/create").mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-456"}
        )
    )

    customer = Customer(email="test@example.com", notify=True)
    client.mbway.create_payment(
        order_id="ORD-002",
        amount=Decimal("10.00"),
        phone_number="912345678",
        customer=customer,
    )

    payload = json.loads(route.calls[0].request.content)
    assert payload["customer"]["email"] == "test@example.com"
    assert payload["customer"]["notify"] is True


@respx.mock
def test_create_payment_sends_api_key_header(client: EupagoClient) -> None:
    route = respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/create").mock(
        return_value=Response(201, json={"transactionStatus": "Success"})
    )

    client.mbway.create_payment(
        order_id="ORD-003",
        amount=Decimal("5.00"),
        phone_number="912345678",
    )

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


def test_create_payment_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.mbway.create_payment(
            order_id="ORD-004",
            amount=Decimal("0"),
            phone_number="912345678",
        )


def test_create_payment_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.mbway.create_payment(
            order_id="ORD-005",
            amount=Decimal("100000"),
            phone_number="912345678",
        )


def test_create_payment_validates_empty_phone(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="phone_number is required"):
        client.mbway.create_payment(
            order_id="ORD-006",
            amount=Decimal("10.00"),
            phone_number="",
        )


@respx.mock
def test_authorize_success(client: EupagoClient) -> None:
    respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/authorize").mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-auth-789"}
        )
    )

    result = client.mbway.authorize(
        order_id="ORD-010",
        amount=Decimal("25.00"),
        phone_number="912345678",
    )

    assert result.transaction_id == "txn-auth-789"
    assert result.status == PaymentStatus.PENDING


@respx.mock
def test_capture_success(client: EupagoClient) -> None:
    respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/capture/txn-auth-789").mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-auth-789"}
        )
    )

    result = client.mbway.capture(
        transaction_id="txn-auth-789",
        amount=Decimal("25.00"),
    )

    assert result.transaction_id == "txn-auth-789"
    assert result.status == PaymentStatus.PAID


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post("https://sandbox.eupago.pt/api/v1.02/mbway/create").mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-async-1"}
        )
    )

    result = await client.mbway.create_payment_async(
        order_id="ORD-ASYNC-001",
        amount=Decimal("15.00"),
        phone_number="912345678",
    )

    assert result.transaction_id == "txn-async-1"
    assert result.method == "mbway"
    await client.aclose()
