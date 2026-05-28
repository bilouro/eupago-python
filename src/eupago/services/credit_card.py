from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.customer import Customer
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("3999")
_PATH_CREATE = f"{API_PREFIX}/creditcard/create"
_PATH_AUTHORIZE = f"{API_PREFIX}/creditcard/authorize"
_PATH_CAPTURE = f"{API_PREFIX}/creditcard/capture"
_PATH_SUBSCRIPTION = f"{API_PREFIX}/creditcard/subscription"
_PATH_SUBSCRIPTION_PAYMENT = f"{API_PREFIX}/creditcard/payment"


def _build_payment_body(
    order_id: str,
    amount: Decimal,
    *,
    currency: str = "EUR",
    customer: Customer | None = None,
    description: str | None = None,
    success_url: str | None = None,
    error_url: str | None = None,
    back_url: str | None = None,
    cancel_url: str | None = None,
    callback_url: str | None = None,
    language: str = "PT",
) -> dict[str, Any]:
    if amount <= 0 or amount > _MAX_AMOUNT:
        raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")

    payment: dict[str, Any] = {
        "amount": {"value": float(amount), "currency": currency},
        "identifier": order_id,
        "lang": language,
    }
    if description:
        payment["description"] = description
    if success_url:
        payment["successUrl"] = success_url
    if error_url:
        payment["failUrl"] = error_url
    if back_url:
        payment["backUrl"] = back_url
    if cancel_url:
        payment["cancelUrl"] = cancel_url
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


def _is_success(data: dict[str, Any]) -> bool:
    return data.get("transactionStatus") == "Success" or data.get("estado") == 0


def _parse_response(
    data: dict[str, Any],
    order_id: str,
    amount: Decimal,
    status: PaymentStatus = PaymentStatus.PENDING,
) -> PaymentResult:
    transaction_id = data.get("transactionID")
    reference = data.get("reference")
    payment_url = data.get("redirectUrl") or data.get("paymentUrl")

    if not _is_success(data):
        status = PaymentStatus.ERROR

    return PaymentResult(
        order_id=order_id,
        amount=amount,
        transaction_id=str(transaction_id) if transaction_id is not None else None,
        reference=str(reference) if reference is not None else None,
        status=status,
        payment_url=payment_url,
        method="credit_card",
        raw_response=data,
    )


class CreditCardService(BaseService):
    def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        cancel_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            cancel_url=cancel_url,
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
        currency: str = "EUR",
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        cancel_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            cancel_url=cancel_url,
            callback_url=callback_url,
            language=language,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)

    def authorize(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
        )
        response = self._request("POST", _PATH_AUTHORIZE, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def authorize_async(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
        )
        response = await self._request_async("POST", _PATH_AUTHORIZE, json=body)
        return _parse_response(response.json(), order_id, amount)

    def capture(self, transaction_id: str) -> PaymentResult:
        path = f"{_PATH_CAPTURE}/{transaction_id}"
        response = self._request("POST", path, json={})
        data = response.json()
        return PaymentResult(
            transaction_id=transaction_id,
            status=PaymentStatus.PAID if _is_success(data) else PaymentStatus.ERROR,
            method="credit_card",
            raw_response=data,
        )

    async def capture_async(self, transaction_id: str) -> PaymentResult:
        path = f"{_PATH_CAPTURE}/{transaction_id}"
        response = await self._request_async("POST", path, json={})
        data = response.json()
        return PaymentResult(
            transaction_id=transaction_id,
            status=PaymentStatus.PAID if _is_success(data) else PaymentStatus.ERROR,
            method="credit_card",
            raw_response=data,
        )

    def create_subscription(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
        )
        response = self._request("POST", _PATH_SUBSCRIPTION, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def create_subscription_async(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
        )
        response = await self._request_async("POST", _PATH_SUBSCRIPTION, json=body)
        return _parse_response(response.json(), order_id, amount)

    def charge_subscription(
        self,
        recurrent_id: int,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(order_id, amount, currency=currency, customer=customer)
        path = f"{_PATH_SUBSCRIPTION_PAYMENT}/{recurrent_id}"
        response = self._request("POST", path, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def charge_subscription_async(
        self,
        recurrent_id: int,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
    ) -> PaymentResult:
        body = _build_payment_body(order_id, amount, currency=currency, customer=customer)
        path = f"{_PATH_SUBSCRIPTION_PAYMENT}/{recurrent_id}"
        response = await self._request_async("POST", path, json=body)
        return _parse_response(response.json(), order_id, amount)
