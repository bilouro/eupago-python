from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.customer import Customer
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{API_PREFIX}/googlepay/create"


def _build_request_body(
    order_id: str,
    amount: Decimal,
    *,
    customer: Customer | None = None,
    description: str | None = None,
    success_url: str | None = None,
    error_url: str | None = None,
    callback_url: str | None = None,
    language: str = "PT",
) -> dict[str, Any]:
    if amount <= 0 or amount > _MAX_AMOUNT:
        raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")

    payment: dict[str, Any] = {
        "amount": float(amount),
        "identifier": order_id,
        "lang": language,
    }
    if description:
        payment["description"] = description
    if success_url:
        payment["successUrl"] = success_url
    if error_url:
        payment["failUrl"] = error_url
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
    payment_url = data.get("redirectUrl") or data.get("paymentUrl")
    estado = data.get("estado", 0)

    return PaymentResult(
        order_id=order_id,
        amount=amount,
        transaction_id=str(transaction_id) if transaction_id else None,
        status=PaymentStatus.PENDING if estado == 0 else PaymentStatus.ERROR,
        payment_url=payment_url,
        method="google_pay",
        raw_response=data,
    )


class GooglePayService(BaseService):
    def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        *,
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            callback_url=callback_url,
            language=language,
        )
        response = self._request("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def create_payment_async(
        self,
        order_id: str,
        amount: Decimal,
        *,
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            callback_url=callback_url,
            language=language,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)
