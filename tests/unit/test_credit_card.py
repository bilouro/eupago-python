from __future__ import annotations

import json
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError
from eupago.models.customer import Customer

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/api/v1.02/creditcard/create"
AUTHORIZE_URL = f"{SANDBOX}/api/v1.02/creditcard/authorize"
CAPTURE_URL = f"{SANDBOX}/api/v1.02/creditcard/capture"
SUBSCRIPTION_URL = f"{SANDBOX}/api/v1.02/creditcard/subscription"
SUBSCRIPTION_PAYMENT_URL = f"{SANDBOX}/api/v1.02/creditcard/payment"


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
                "transactionID": "txn-cc-001",
                "reference": "306195",
                "redirectUrl": "https://sandbox.eupago.pt/api/extern/creditcard/form/txn-cc-001",
            },
        )
    )

    result = client.credit_card.create_payment(
        order_id="ORD-CC-001",
        amount=Decimal("99.99"),
        success_url="https://loja.pt/ok",
        error_url="https://loja.pt/fail",
        back_url="https://loja.pt/back",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["amount"] == {"value": 99.99, "currency": "EUR"}
    assert body["payment"]["backUrl"] == "https://loja.pt/back"

    assert result.transaction_id == "txn-cc-001"
    assert result.reference == "306195"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url.endswith("/creditcard/form/txn-cc-001")
    assert result.method == "credit_card"


@respx.mock
def test_create_payment_sends_header_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "txn-1"})
    )

    client.credit_card.create_payment(order_id="ORD-CC-002", amount=Decimal("10.00"))

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_with_all_urls(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "txn-2"})
    )

    client.credit_card.create_payment(
        order_id="ORD-CC-003",
        amount=Decimal("50.00"),
        success_url="https://shop.com/ok",
        error_url="https://shop.com/fail",
        back_url="https://shop.com/back",
        cancel_url="https://shop.com/cancel",
        callback_url="https://shop.com/webhook",
        description="Premium plan",
        language="EN",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["successUrl"] == "https://shop.com/ok"
    assert body["payment"]["failUrl"] == "https://shop.com/fail"
    assert body["payment"]["backUrl"] == "https://shop.com/back"
    assert body["payment"]["cancelUrl"] == "https://shop.com/cancel"
    assert body["payment"]["adminCallback"] == "https://shop.com/webhook"
    assert body["payment"]["description"] == "Premium plan"
    assert body["payment"]["lang"] == "EN"


def test_create_payment_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.credit_card.create_payment(order_id="ORD-CC-004", amount=Decimal("0"))


def test_create_payment_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.credit_card.create_payment(order_id="ORD-CC-005", amount=Decimal("4000"))


@respx.mock
def test_create_payment_error_status(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            200, json={"transactionStatus": "Rejected", "code": "AMOUNT_MISSING", "text": "Amount"}
        )
    )

    result = client.credit_card.create_payment(order_id="ORD-CC-006", amount=Decimal("10.00"))

    assert result.status == PaymentStatus.ERROR


@respx.mock
def test_authorize_success(client: EupagoClient) -> None:
    respx.post(AUTHORIZE_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionID": "txn-auth-cc-001",
                "estado": 0,
                "redirectUrl": "https://pay.eupago.pt/cc/3ds-auth",
            },
        )
    )

    result = client.credit_card.authorize(
        order_id="ORD-CC-AUTH-001",
        amount=Decimal("200.00"),
        success_url="https://loja.pt/ok",
    )

    assert result.transaction_id == "txn-auth-cc-001"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url == "https://pay.eupago.pt/cc/3ds-auth"


@respx.mock
def test_capture_success(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-auth-cc-001").mock(
        return_value=Response(201, json={"transactionID": "txn-auth-cc-001", "estado": 0})
    )

    result = client.credit_card.capture(transaction_id="txn-auth-cc-001")

    assert result.transaction_id == "txn-auth-cc-001"
    assert result.status == PaymentStatus.PAID


@respx.mock
def test_capture_error(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-fail").mock(return_value=Response(200, json={"estado": -1}))

    result = client.credit_card.capture(transaction_id="txn-fail")

    assert result.status == PaymentStatus.ERROR


@respx.mock
def test_create_subscription_success(client: EupagoClient) -> None:
    respx.post(SUBSCRIPTION_URL).mock(
        return_value=Response(
            200,
            json={
                "transactionID": "sub-001",
                "estado": 0,
                "redirectUrl": "https://pay.eupago.pt/cc/sub-form",
            },
        )
    )

    result = client.credit_card.create_subscription(
        order_id="SUB-001",
        amount=Decimal("9.99"),
        success_url="https://loja.pt/sub-ok",
    )

    assert result.transaction_id == "sub-001"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url == "https://pay.eupago.pt/cc/sub-form"


@respx.mock
def test_charge_subscription_success(client: EupagoClient) -> None:
    respx.post(f"{SUBSCRIPTION_PAYMENT_URL}/42").mock(
        return_value=Response(200, json={"transactionID": "charge-001", "estado": 0})
    )

    result = client.credit_card.charge_subscription(
        recurrent_id=42,
        order_id="CHARGE-001",
        amount=Decimal("9.99"),
    )

    assert result.transaction_id == "charge-001"
    assert result.status == PaymentStatus.PENDING


@respx.mock
def test_charge_subscription_with_customer(client: EupagoClient) -> None:
    route = respx.post(f"{SUBSCRIPTION_PAYMENT_URL}/42").mock(
        return_value=Response(200, json={"estado": 0, "transactionID": "charge-002"})
    )

    customer = Customer(email="subscriber@example.com")
    client.credit_card.charge_subscription(
        recurrent_id=42,
        order_id="CHARGE-002",
        amount=Decimal("9.99"),
        customer=customer,
    )

    body = json.loads(route.calls[0].request.content)
    assert body["customer"]["email"] == "subscriber@example.com"


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"transactionID": "txn-async-cc", "estado": 0})
    )

    result = await client.credit_card.create_payment_async(
        order_id="ORD-CC-ASYNC",
        amount=Decimal("25.00"),
    )

    assert result.transaction_id == "txn-async-cc"
    assert result.method == "credit_card"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_authorize_async(client: EupagoClient) -> None:
    respx.post(AUTHORIZE_URL).mock(
        return_value=Response(201, json={"transactionID": "txn-auth-async", "estado": 0})
    )

    result = await client.credit_card.authorize_async(
        order_id="ORD-CC-AUTH-ASYNC",
        amount=Decimal("100.00"),
    )

    assert result.transaction_id == "txn-auth-async"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_capture_async(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-cap-async").mock(
        return_value=Response(201, json={"estado": 0, "transactionID": "txn-cap-async"})
    )

    result = await client.credit_card.capture_async(transaction_id="txn-cap-async")

    assert result.status == PaymentStatus.PAID
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_create_subscription_async(client: EupagoClient) -> None:
    respx.post(SUBSCRIPTION_URL).mock(
        return_value=Response(200, json={"transactionID": "sub-async", "estado": 0})
    )

    result = await client.credit_card.create_subscription_async(
        order_id="SUB-ASYNC",
        amount=Decimal("19.99"),
    )

    assert result.transaction_id == "sub-async"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_charge_subscription_async(client: EupagoClient) -> None:
    respx.post(f"{SUBSCRIPTION_PAYMENT_URL}/99").mock(
        return_value=Response(200, json={"transactionID": "charge-async", "estado": 0})
    )

    result = await client.credit_card.charge_subscription_async(
        recurrent_id=99,
        order_id="CHARGE-ASYNC",
        amount=Decimal("19.99"),
    )

    assert result.transaction_id == "charge-async"
    await client.aclose()
