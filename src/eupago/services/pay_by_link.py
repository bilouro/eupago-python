from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.customer import Customer
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{API_PREFIX}/paybylink/create"


def _is_success(data: dict[str, Any]) -> bool:
    return data.get("transactionStatus") == "Success" or data.get("estado") == 0


def _build_request_body(
    order_id: str,
    amount: Decimal,
    *,
    currency: str = "EUR",
    customer: Customer | None = None,
    success_url: str | None = None,
    error_url: str | None = None,
    back_url: str | None = None,
    expires_at: datetime | None = None,
    shipping: Decimal | None = None,
    language: str = "PT",
    products: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if amount <= 0 or amount > _MAX_AMOUNT:
        raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")

    payment: dict[str, Any] = {
        "identifier": order_id,
        "amount": {"value": float(amount), "currency": currency},
        "lang": language,
    }
    if shipping is not None:
        payment["shipping"] = {"value": float(shipping), "currency": currency}
    if expires_at is not None:
        payment["expirationDate"] = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    if success_url:
        payment["successUrl"] = success_url
    if error_url:
        payment["failUrl"] = error_url
    if back_url:
        payment["backUrl"] = back_url

    body: dict[str, Any] = {"payment": payment}

    if products:
        body["products"] = products

    if customer:
        cust: dict[str, Any] = {"notify": customer.notify}
        if customer.email:
            cust["email"] = customer.email
        if customer.name:
            cust["nome"] = customer.name
        body["customer"] = cust

    return body


def _parse_response(data: dict[str, Any], order_id: str, amount: Decimal) -> PaymentResult:
    transaction_id = data.get("transactionID")
    payment_url = data.get("redirectUrl") or data.get("paymentUrl")
    return PaymentResult(
        order_id=order_id,
        amount=amount,
        transaction_id=str(transaction_id) if transaction_id is not None else None,
        status=PaymentStatus.PENDING if _is_success(data) else PaymentStatus.ERROR,
        payment_url=payment_url,
        method="pay_by_link",
        raw_response=data,
    )


class PayByLinkService(BaseService):
    """Pay By Link — eupago-hosted checkout page.

    Generate a single URL the customer opens to choose how to pay (MB WAY,
    Multibanco, Card, Apple/Google Pay, Cofidis, …). No checkout/website is
    needed on your side. Best suited to invoices, social-commerce flows, B2B
    billing, or anywhere the customer picks the method.

    The response carries the ``payment_url`` (the customer-facing link) and a
    ``transaction_id``. The final outcome arrives via the standard payment
    webhook once the customer completes the flow on eupago's page.
    """

    def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        *,
        currency: str = "EUR",
        customer: Customer | None = None,
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        expires_at: datetime | None = None,
        shipping: Decimal | None = None,
        language: str = "PT",
        products: list[dict[str, Any]] | None = None,
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            expires_at=expires_at,
            shipping=shipping,
            language=language,
            products=products,
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
        success_url: str | None = None,
        error_url: str | None = None,
        back_url: str | None = None,
        expires_at: datetime | None = None,
        shipping: Decimal | None = None,
        language: str = "PT",
        products: list[dict[str, Any]] | None = None,
    ) -> PaymentResult:
        body = _build_request_body(
            order_id,
            amount,
            currency=currency,
            customer=customer,
            success_url=success_url,
            error_url=error_url,
            back_url=back_url,
            expires_at=expires_at,
            shipping=shipping,
            language=language,
            products=products,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), order_id, amount)
