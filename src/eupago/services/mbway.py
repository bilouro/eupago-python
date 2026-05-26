from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.customer import Customer
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{API_PREFIX}/mbway/create"
_PATH_AUTHORIZE = f"{API_PREFIX}/mbway/authorize"
_PATH_CAPTURE = f"{API_PREFIX}/mbway/capture"


def _build_request_body(
    order_id: str,
    amount: Decimal,
    phone_number: str,
    *,
    customer: Customer | None = None,
    description: str | None = None,
    callback_url: str | None = None,
    language: str = "PT",
) -> dict[str, Any]:
    if amount <= 0 or amount > _MAX_AMOUNT:
        raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")
    if not phone_number:
        raise ValidationError("phone_number is required for MB WAY")

    payment: dict[str, Any] = {
        "amount": float(amount),
        "identifier": order_id,
        "alias": phone_number,
        "lang": language,
    }
    if description:
        payment["description"] = description
    if callback_url:
        payment["adminCallback"] = callback_url

    body: dict[str, Any] = {"payment": payment}

    if customer:
        cust: dict[str, Any] = {"notify": customer.notify}
        if customer.email:
            cust["email"] = customer.email
        if customer.phone_number:
            cust["phone"] = customer.phone_number
        body["customer"] = cust

    return body


def _parse_response(data: dict[str, Any], order_id: str, amount: Decimal) -> PaymentResult:
    transaction_id = data.get("transactionID") or data.get("referencia")
    status_raw = data.get("estado", 0)
    status = PaymentStatus.PENDING if status_raw == 0 else PaymentStatus.ERROR

    return PaymentResult(
        order_id=order_id,
        amount=amount,
        transaction_id=str(transaction_id) if transaction_id else None,
        status=status,
        method="mbway",
        raw_response=data,
    )


class MBWayService(BaseService):
    def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        phone_number: str,
        *,
        customer: Customer | None = None,
        description: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            phone_number,
            customer=customer,
            description=description,
            callback_url=callback_url,
            language=language,
        )
        response = self._request("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def create_payment_async(
        self,
        order_id: str,
        amount: Decimal,
        phone_number: str,
        *,
        customer: Customer | None = None,
        description: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            phone_number,
            customer=customer,
            description=description,
            callback_url=callback_url,
            language=language,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)

    def authorize(
        self,
        order_id: str,
        amount: Decimal,
        phone_number: str,
        *,
        customer: Customer | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_request_body(
            order_id, amount, phone_number, customer=customer, callback_url=callback_url
        )
        response = self._request("POST", _PATH_AUTHORIZE, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def authorize_async(
        self,
        order_id: str,
        amount: Decimal,
        phone_number: str,
        *,
        customer: Customer | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_request_body(
            order_id, amount, phone_number, customer=customer, callback_url=callback_url
        )
        response = await self._request_async("POST", _PATH_AUTHORIZE, json=body)
        return _parse_response(response.json(), order_id, amount)

    def capture(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> PaymentResult:
        body: dict[str, Any] = {"payment": {"amount": float(amount)}}
        path = f"{_PATH_CAPTURE}/{transaction_id}"
        response = self._request("POST", path, json=body)
        data = response.json()
        return PaymentResult(
            transaction_id=transaction_id,
            amount=amount,
            status=PaymentStatus.PAID if data.get("estado", -1) == 0 else PaymentStatus.ERROR,
            method="mbway",
            raw_response=data,
        )

    async def capture_async(
        self,
        transaction_id: str,
        amount: Decimal,
    ) -> PaymentResult:
        body: dict[str, Any] = {"payment": {"amount": float(amount)}}
        path = f"{_PATH_CAPTURE}/{transaction_id}"
        response = await self._request_async("POST", path, json=body)
        data = response.json()
        return PaymentResult(
            transaction_id=transaction_id,
            amount=amount,
            status=PaymentStatus.PAID if data.get("estado", -1) == 0 else PaymentStatus.ERROR,
            method="mbway",
            raw_response=data,
        )
