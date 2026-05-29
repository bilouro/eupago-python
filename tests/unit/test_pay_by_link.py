from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import Customer, EupagoClient, PaymentStatus, ValidationError

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/paybylink/create"

_REAL_RESPONSE = {
    "transactionStatus": "Success",
    "transactionID": "af3df607c6724870be962a69cac30b99",
    "status": "Pendente",
    "redirectUrl": "https://sandbox.eupago.pt/api/extern/paybylink/form/af3df607c6724870be962a69cac30b99",
}


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_payment_returns_url(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(return_value=Response(201, json=_REAL_RESPONSE))

    result = client.pay_by_link.create_payment(order_id="ORD-PBL-001", amount=Decimal("49.90"))

    body = json.loads(route.calls[0].request.content)
    assert body == {
        "payment": {
            "identifier": "ORD-PBL-001",
            "amount": {"value": 49.90, "currency": "EUR"},
            "lang": "PT",
        }
    }
    assert result.transaction_id == "af3df607c6724870be962a69cac30b99"
    assert result.payment_url == _REAL_RESPONSE["redirectUrl"]
    assert result.status == PaymentStatus.PENDING
    assert result.method == "pay_by_link"
    assert result.amount == Decimal("49.90")


@respx.mock
def test_create_payment_full_options(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(return_value=Response(201, json=_REAL_RESPONSE))

    expires = datetime(2026, 12, 31, 23, 59, 59)
    customer = Customer(name="Joana Silva", email="joana@example.com", notify=True)

    client.pay_by_link.create_payment(
        order_id="ORD-PBL-002",
        amount=Decimal("120.00"),
        customer=customer,
        success_url="https://shop.example.com/ok",
        error_url="https://shop.example.com/fail",
        back_url="https://shop.example.com/back",
        expires_at=expires,
        shipping=Decimal("5.50"),
        language="EN",
        products=[{"sku": "BOOK-1", "name": "Pilates Guide", "value": 120.00, "quantity": 1}],
    )

    body = json.loads(route.calls[0].request.content)
    payment = body["payment"]
    assert payment["identifier"] == "ORD-PBL-002"
    assert payment["amount"] == {"value": 120.00, "currency": "EUR"}
    assert payment["shipping"] == {"value": 5.50, "currency": "EUR"}
    assert payment["expirationDate"] == "2026-12-31 23:59:59"
    assert payment["successUrl"] == "https://shop.example.com/ok"
    assert payment["failUrl"] == "https://shop.example.com/fail"
    assert payment["backUrl"] == "https://shop.example.com/back"
    assert payment["lang"] == "EN"
    assert body["customer"] == {
        "notify": True,
        "email": "joana@example.com",
        "nome": "Joana Silva",
    }
    assert body["products"][0]["sku"] == "BOOK-1"


def test_create_payment_rejects_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.pay_by_link.create_payment(order_id="ORD-PBL-BAD", amount=Decimal("0"))


@respx.mock
def test_create_payment_uses_header_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(return_value=Response(201, json=_REAL_RESPONSE))

    client.pay_by_link.create_payment(order_id="ORD-PBL-AUTH", amount=Decimal("10.00"))

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_rejected_returns_error(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(200, json={"transactionStatus": "Rejected"}))

    result = client.pay_by_link.create_payment(order_id="ORD-PBL-REJ", amount=Decimal("10.00"))

    assert result.status == PaymentStatus.ERROR


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(201, json=_REAL_RESPONSE))

    result = await client.pay_by_link.create_payment_async(
        order_id="ORD-PBL-ASYNC",
        amount=Decimal("15.00"),
    )

    assert result.transaction_id == "af3df607c6724870be962a69cac30b99"
    assert result.payment_url == _REAL_RESPONSE["redirectUrl"]
    assert result.method == "pay_by_link"
    await client.aclose()
