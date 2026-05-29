from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
import respx
from httpx import Response

from eupago import EupagoClient, PaymentStatus, ValidationError
from eupago.exceptions import ApiError

SANDBOX = "https://sandbox.eupago.pt"
CREATE_URL = f"{SANDBOX}/clientes/rest_api/multibanco/create"
INFO_URL = f"{SANDBOX}/clientes/rest_api/multibanco/info"


@pytest.fixture
def client() -> EupagoClient:
    return EupagoClient(api_key="test-0000-0000-0000-0000", sandbox=True)


@respx.mock
def test_create_reference_success(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            200,
            json={"estado": 0, "entidade": 11249, "referencia": 999888777, "valor": 49.90},
        )
    )

    result = client.multibanco.create_reference(
        order_id="ORD-001",
        amount=Decimal("49.90"),
    )

    assert result.entity == "11249"
    assert result.reference == "999888777"
    assert result.status == PaymentStatus.PENDING
    assert result.amount == Decimal("49.90")
    assert result.method == "multibanco"


@respx.mock
def test_create_reference_sends_body_auth(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "entidade": 11249, "referencia": 123})
    )

    client.multibanco.create_reference(order_id="ORD-002", amount=Decimal("10.00"))

    body = json.loads(route.calls[0].request.content)
    assert body["chave"] == "test-0000-0000-0000-0000"
    assert body["valor"] == 10.0
    assert body["id"] == "ORD-002"
    assert body["per_dup"] == 0


@respx.mock
def test_create_reference_with_expiry(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "entidade": 11249, "referencia": 123})
    )

    client.multibanco.create_reference(
        order_id="ORD-003",
        amount=Decimal("25.00"),
        expires_at=date(2026, 6, 30),
        starts_at=date(2026, 5, 27),
        send_expiry_reminder=True,
        email="test@example.com",
    )

    body = json.loads(route.calls[0].request.content)
    assert body["data_fim"] == "2026-06-30"
    assert body["data_inicio"] == "2026-05-27"
    assert body["failOver"] == "1"
    assert body["email"] == "test@example.com"


@respx.mock
def test_create_reference_allow_duplicate(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "entidade": 11249, "referencia": 123})
    )

    client.multibanco.create_reference(
        order_id="ORD-004",
        amount=Decimal("15.00"),
        allow_duplicate=True,
    )

    body = json.loads(route.calls[0].request.content)
    assert body["per_dup"] == 1


@respx.mock
def test_create_reference_with_amount_range(client: EupagoClient) -> None:
    route = respx.post(CREATE_URL).mock(
        return_value=Response(200, json={"estado": 0, "entidade": 11249, "referencia": 123})
    )

    client.multibanco.create_reference(
        order_id="ORD-005",
        amount=Decimal("50.00"),
        min_amount=Decimal("10.00"),
        max_amount=Decimal("100.00"),
    )

    body = json.loads(route.calls[0].request.content)
    assert body["valor_minimo"] == 10.0
    assert body["valor_maximo"] == 100.0


def test_create_reference_validates_zero_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.multibanco.create_reference(order_id="ORD-006", amount=Decimal("0"))


def test_create_reference_validates_max_amount(client: EupagoClient) -> None:
    with pytest.raises(ValidationError, match="Amount must be between"):
        client.multibanco.create_reference(order_id="ORD-007", amount=Decimal("100000"))


@respx.mock
def test_create_reference_invalid_key_raises(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(200, json={"estado": -10}))

    with pytest.raises(ApiError, match="Invalid API key"):
        client.multibanco.create_reference(order_id="ORD-008", amount=Decimal("10.00"))


@respx.mock
def test_create_reference_wrong_values_raises(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(return_value=Response(200, json={"estado": -9}))

    with pytest.raises(ApiError, match="Invalid parameter"):
        client.multibanco.create_reference(order_id="ORD-009", amount=Decimal("10.00"))


@respx.mock
def test_get_info_paid(client: EupagoClient) -> None:
    respx.post(INFO_URL).mock(
        return_value=Response(
            200,
            json={
                "estado": 0,
                "entidade": 11249,
                "referencia": 999888777,
                "identificador": "ORD-001",
                "estado_referencia": "paga",
                "pagamentos": [
                    {"trid": 78901, "estado": "paga", "valor": "49.90000", "comissao": "0.68000"}
                ],
                "sucesso": True,
            },
        )
    )

    result = client.multibanco.get_info(reference="999888777", entity="11249")

    assert result.status == PaymentStatus.PAID
    assert result.reference == "999888777"
    assert result.entity == "11249"
    assert result.amount == Decimal("49.90")
    assert result.transaction_id == "78901"
    assert result.order_id == "ORD-001"


@respx.mock
def test_get_info_pending(client: EupagoClient) -> None:
    respx.post(INFO_URL).mock(
        return_value=Response(
            200,
            json={
                "estado": 0,
                "entidade": 11249,
                "referencia": 999888777,
                "identificador": "ORD-001",
                "estado_referencia": "pendente",
                "sucesso": True,
            },
        )
    )

    result = client.multibanco.get_info(reference="999888777")

    assert result.status == PaymentStatus.PENDING


@respx.mock
def test_get_info_sends_body_auth(client: EupagoClient) -> None:
    route = respx.post(INFO_URL).mock(
        return_value=Response(
            200,
            json={"estado": 0, "entidade": 11249, "referencia": 123, "valor": 10.0},
        )
    )

    client.multibanco.get_info(reference="123", entity="11249")

    body = json.loads(route.calls[0].request.content)
    assert body["chave"] == "test-0000-0000-0000-0000"
    assert body["referencia"] == "123"
    assert body["entidade"] == "11249"


@respx.mock
def test_get_info_not_found_raises(client: EupagoClient) -> None:
    respx.post(INFO_URL).mock(return_value=Response(200, json={"estado": -11}))

    with pytest.raises(ApiError, match="Payment not found"):
        client.multibanco.get_info(reference="000000000")


@respx.mock
@pytest.mark.asyncio
async def test_create_reference_async(client: EupagoClient) -> None:
    respx.post(CREATE_URL).mock(
        return_value=Response(
            200,
            json={"estado": 0, "entidade": 11249, "referencia": 555666777, "valor": 30.0},
        )
    )

    result = await client.multibanco.create_reference_async(
        order_id="ORD-ASYNC-001",
        amount=Decimal("30.00"),
    )

    assert result.entity == "11249"
    assert result.reference == "555666777"
    assert result.method == "multibanco"
    await client.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_get_info_async(client: EupagoClient) -> None:
    respx.post(INFO_URL).mock(
        return_value=Response(
            200,
            json={
                "estado": 0,
                "entidade": 11249,
                "referencia": 555666777,
                "estado_referencia": "paga",
                "pagamentos": [{"trid": 90123, "estado": "paga", "valor": "30.00000"}],
            },
        )
    )

    result = await client.multibanco.get_info_async(reference="555666777")

    assert result.status == PaymentStatus.PAID
    await client.aclose()
