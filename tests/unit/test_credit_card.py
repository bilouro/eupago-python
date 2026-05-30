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
                "redirectUrl": f"{SANDBOX}/api/extern/creditcard/form/txn-cc-001",
            },
        )
    )

    result = client.credit_card.create_payment(
        order_id="ORD-CC-001",
        amount=Decimal("99.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["payment"]["amount"] == {"value": 99.99, "currency": "EUR"}
    assert body["payment"]["backUrl"] == "https://shop.pt/back"
    assert body["payment"]["successUrl"] == "https://shop.pt/ok"
    assert body["payment"]["failUrl"] == "https://shop.pt/fail"

    assert result.transaction_id == "txn-cc-001"
    assert result.reference == "306195"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url.endswith("/creditcard/form/txn-cc-001")
    assert result.method == "credit_card"


@respx.mock
def test_create_payment_sends_header_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"transactionStatus": "Success"})
    )

    client.credit_card.create_payment(
        order_id="ORD-CC-002",
        amount=Decimal("10.00"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-0000-0000-0000-0000"


@respx.mock
def test_create_payment_with_customer(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(201, json={"transactionStatus": "Success"})
    )

    client.credit_card.create_payment(
        order_id="ORD-CC-003",
        amount=Decimal("50.00"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
        customer=Customer(email="buyer@example.com", notify=True),
        description="Premium plan",
        language="EN",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["customer"] == {"notify": True, "email": "buyer@example.com"}
    assert body["payment"]["description"] == "Premium plan"
    assert body["payment"]["lang"] == "EN"


def test_create_payment_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.credit_card.create_payment(order_id="ORD-CC-MAX", amount=Decimal("4000"))


def test_create_payment_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.credit_card.create_payment(order_id="ORD-CC-ZERO", amount=Decimal("0"))


@respx.mock
def test_create_payment_rejected_returns_error_status(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            200,
            json={"transactionStatus": "Rejected", "code": "URL_INVALID", "text": "Url is invalid"},
        )
    )

    result = client.credit_card.create_payment(
        order_id="ORD-CC-REJ",
        amount=Decimal("99.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert result.status == PaymentStatus.ERROR


@respx.mock
def test_authorize_success(client: EupagoClient) -> None:
    respx.post(AUTHORIZE_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "transactionID": "txn-auth-001",
                "reference": "306200",
                "redirectUrl": f"{SANDBOX}/api/extern/creditcard/form/txn-auth-001",
            },
        )
    )

    result = client.credit_card.authorize(
        order_id="ORD-CC-AUTH-001",
        amount=Decimal("120.00"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert result.transaction_id == "txn-auth-001"
    assert result.status == PaymentStatus.PENDING
    assert result.payment_url is not None


@respx.mock
def test_capture_success(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-auth-001").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    route = respx.post(f"{CAPTURE_URL}/txn-auth-001").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    result = client.credit_card.capture(transaction_id="txn-auth-001", amount=Decimal("50.00"))

    # cc capture sends the full payment body (amount object), not an empty {}
    payload = json.loads(route.calls[0].request.content)
    assert payload["payment"]["amount"] == {"value": 50.0, "currency": "EUR"}
    assert result.transaction_id == "txn-auth-001"
    assert result.status == PaymentStatus.PAID
    assert result.method == "credit_card"


@respx.mock
def test_capture_failure(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-bad").mock(
        return_value=Response(200, json={"transactionStatus": "Rejected"})
    )

    result = client.credit_card.capture(transaction_id="txn-bad", amount=Decimal("10.00"))

    assert result.status == PaymentStatus.ERROR


@respx.mock
def test_create_subscription_success(client: EupagoClient) -> None:
    respx.post(SUBSCRIPTION_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "transactionID": "sub-001",
                "reference": "RECUR-1",
                "redirectUrl": f"{SANDBOX}/api/extern/creditcard/form/sub-001",
            },
        )
    )

    result = client.credit_card.create_subscription(
        order_id="ORD-SUB-001",
        amount=Decimal("19.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert result.transaction_id == "sub-001"
    assert result.payment_url is not None


@respx.mock
def test_charge_subscription_success(client: EupagoClient) -> None:
    respx.post(f"{SUBSCRIPTION_PAYMENT_URL}/sub-001").mock(
        return_value=Response(
            200,
            json={
                "transactionStatus": "Success",
                "transactionID": "charge-001",
                "reference": "CHG-1",
            },
        )
    )

    result = client.credit_card.charge_subscription(
        recurrent_id="sub-001",
        order_id="ORD-CHG-001",
        amount=Decimal("19.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert result.transaction_id == "charge-001"
    assert result.method == "credit_card"


@respx.mock
@pytest.mark.asyncio
async def test_create_payment_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            201,
            json={"transactionStatus": "Success", "transactionID": "txn-async-cc"},
        )
    )

    result = await client.credit_card.create_payment_async(
        order_id="ORD-CC-ASYNC",
        amount=Decimal("25.00"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )

    assert result.transaction_id == "txn-async-cc"
    assert result.method == "credit_card"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_capture_async_success(client: EupagoClient) -> None:
    respx.post(f"{CAPTURE_URL}/txn-async-auth").mock(
        return_value=Response(200, json={"transactionStatus": "Success"})
    )

    result = await client.credit_card.capture_async(
        transaction_id="txn-async-auth", amount=Decimal("10.00")
    )
    assert result.status == PaymentStatus.PAID
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_authorize_async_success(client: EupagoClient) -> None:
    respx.post(AUTHORIZE_URL).mock(
        return_value=Response(
            201, json={"transactionStatus": "Success", "transactionID": "txn-async-auth"}
        )
    )

    result = await client.credit_card.authorize_async(
        order_id="ORD-CC-ASYNC-AUTH",
        amount=Decimal("25.00"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )
    assert result.transaction_id == "txn-async-auth"
    assert result.status == PaymentStatus.PENDING
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_create_subscription_async_success(client: EupagoClient) -> None:
    route = respx.post(SUBSCRIPTION_URL).mock(
        return_value=Response(
            201,
            json={
                "transactionStatus": "Success",
                "subscriptionID": "async-sub-001",
                "referenceSubs": "ASYNC-REC-1",
                "redirectUrl": f"{SANDBOX}/api/extern/creditcard/formsub/async-sub-001",
            },
        )
    )

    result = await client.credit_card.create_subscription_async(
        order_id="ORD-SUB-ASYNC",
        amount=Decimal("9.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )
    payload = json.loads(route.calls[0].request.content)
    # Verified field: subscription block is required (without it eupago 500s).
    assert "subscription" in payload["payment"]
    assert payload["payment"]["subscription"]["periodicity"] == "Mensal"
    # subscriptionID maps to transaction_id on the SDK side.
    assert result.transaction_id == "async-sub-001"
    assert result.reference == "ASYNC-REC-1"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_charge_subscription_async_success(client: EupagoClient) -> None:
    respx.post(f"{SUBSCRIPTION_PAYMENT_URL}/async-sub-001").mock(
        return_value=Response(
            200,
            json={
                "transactionStatus": "Success",
                "status": "Paid",
                "transactionID": "charge-async-001",
                "reference": "CHG-A-1",
            },
        )
    )

    result = await client.credit_card.charge_subscription_async(
        recurrent_id="async-sub-001",
        order_id="ORD-CHG-ASYNC",
        amount=Decimal("9.99"),
        success_url="https://shop.pt/ok",
        error_url="https://shop.pt/fail",
        back_url="https://shop.pt/back",
    )
    assert result.transaction_id == "charge-async-001"
    await client.aclose()
