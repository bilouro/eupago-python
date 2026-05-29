from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import MANAGEMENT_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_PATH_REFUND = f"{MANAGEMENT_PREFIX}/refund"


def _build_body(
    value: Decimal,
    *,
    currency: str = "EUR",
    reason: str | None = None,
) -> dict[str, Any]:
    if value <= 0:
        raise ValidationError("Refund value must be positive")
    body: dict[str, Any] = {"value": float(value), "currency": currency}
    if reason:
        body["motivo"] = reason
    return body


def _parse_response(data: dict[str, Any], transaction_id: str, value: Decimal) -> PaymentResult:
    status_raw = data.get("transactionStatus")
    success = status_raw == "Success" or data.get("estado") == 0
    return PaymentResult(
        transaction_id=transaction_id,
        amount=value,
        status=PaymentStatus.REFUNDED if success else PaymentStatus.ERROR,
        method="refund",
        raw_response=data,
    )


class RefundService(BaseService):
    """Refunds via the management API.

    Requires OAuth credentials (``client_id`` + ``client_secret`` on the
    ``EupagoClient``). The same secret pair gates every ``/api/management/...``
    endpoint.

    **Getting the OAuth credentials:** these are NOT the API key and are not
    self-service in the backoffice. As of writing, eupago issues
    ``client_id`` / ``client_secret`` on request via their support portal
    (`customer.support.eupago.com <https://customer.support.eupago.com>`_).
    The ``/api/auth/token`` endpoint accepts ``grant_type=client_credentials``
    (preferred) or ``grant_type=password`` (with the backoffice
    username/password) — both still require the ``client_id`` / ``client_secret``
    pair.

    **No refund webhook:** the eupago docs state explicitly that there are no
    webhook notifications for refunded transactions. Verify the refund via the
    response itself (``status == PaymentStatus.REFUNDED``) and, if you need a
    second source of truth, by polling the management transactions endpoint.
    """

    _default_auth: str = "oauth"

    def refund(
        self,
        transaction_id: str,
        value: Decimal,
        *,
        currency: str = "EUR",
        reason: str | None = None,
    ) -> PaymentResult:
        body = _build_body(value, currency=currency, reason=reason)
        path = f"{_PATH_REFUND}/{transaction_id}"
        response = self._request("POST", path, json=body)
        return _parse_response(response.json(), transaction_id, value)

    async def refund_async(
        self,
        transaction_id: str,
        value: Decimal,
        *,
        currency: str = "EUR",
        reason: str | None = None,
    ) -> PaymentResult:
        body = _build_body(value, currency=currency, reason=reason)
        path = f"{_PATH_REFUND}/{transaction_id}"
        response = await self._request_async("POST", path, json=body)
        return _parse_response(response.json(), transaction_id, value)
