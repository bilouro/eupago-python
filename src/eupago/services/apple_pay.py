from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.customer import Customer
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{API_PREFIX}/applepay/create"


def _is_success(data: dict[str, Any]) -> bool:
    return data.get("transactionStatus") == "Success" or data.get("estado") == 0


def _build_request_body(
    order_id: str,
    amount: Decimal,
    apple_pay_token: str | None,
    *,
    currency: str = "EUR",
    customer: Customer | None = None,
    description: str | None = None,
    success_url: str | None = None,
    error_url: str | None = None,
    back_url: str | None = None,
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
    if apple_pay_token:
        payment["applePayToken"] = apple_pay_token
    if description:
        payment["description"] = description
    if success_url:
        payment["successUrl"] = success_url
    if error_url:
        payment["failUrl"] = error_url
    if back_url:
        payment["backUrl"] = back_url
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
    return PaymentResult(
        order_id=order_id,
        amount=amount,
        transaction_id=str(data["transactionID"]) if data.get("transactionID") else None,
        reference=str(data["reference"]) if data.get("reference") else None,
        status=PaymentStatus.PENDING if _is_success(data) else PaymentStatus.ERROR,
        payment_url=data.get("redirectUrl") or data.get("paymentUrl"),
        method="apple_pay",
        raw_response=data,
    )


class ApplePayService(BaseService):
    """Apple Pay payments.

    Two flows are supported:

    - **Hosted (recommended for web):** call ``create_payment`` without
      ``apple_pay_token``. eupago returns a ``redirectUrl`` (exposed as
      ``PaymentResult.payment_url``) that hosts the Apple Pay sheet —
      redirect the customer's browser there. This is the simplest
      integration and works without an Apple Developer Program account
      on your side (eupago is the merchant).
    - **Native (mobile / web with own merchant id):** obtain a
      ``PKPaymentToken`` via the Apple Pay JS / iOS SDK and pass it as
      ``apple_pay_token``. eupago decrypts it server-side and charges
      the card directly — no redirect.

    Body shape mirrors the verified credit-card v1.02 contract; the
    ``applePayToken`` field name follows eupago's naming convention.
    """

    def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        apple_pay_token: str | None = None,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            apple_pay_token,
            currency=currency,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
            language=language,
        )
        response = self._request("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)

    async def create_payment_async(
        self,
        order_id: str,
        amount: Decimal,
        apple_pay_token: str | None = None,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        description: str | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        callback_url: str | None = None,
        language: str = "PT",
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            apple_pay_token,
            currency=currency,
            customer=customer,
            description=description,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            callback_url=callback_url,
            language=language,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)
