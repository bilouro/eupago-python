from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import MANAGEMENT_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_PATH_REFUND = f"{MANAGEMENT_PREFIX}/refund"


def _build_body(
    amount: Decimal,
    *,
    reason: str | None = None,
    iban: str | None = None,
    bic: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise ValidationError("Refund amount must be positive")
    body: dict[str, Any] = {"amount": float(amount)}
    if reason:
        body["reason"] = reason
    if iban:
        body["iban"] = iban
    if bic:
        body["bic"] = bic
    return body


def _parse_response(data: dict[str, Any], transaction_id: str, amount: Decimal) -> PaymentResult:
    # Live-verified shape (sandbox, May 2026):
    #   201 {"transactionStatus": "Success", "refundId": "2788",
    #        "status": "Reembolsado"}
    success = data.get("transactionStatus") == "Success" or data.get("estado") == 0
    return PaymentResult(
        transaction_id=transaction_id,
        amount=amount,
        status=PaymentStatus.REFUNDED if success else PaymentStatus.ERROR,
        method="refund",
        # The eupago refundId lives in raw_response — kept opaque on PaymentResult
        # because callers usually only need it for reconciliation / audit logs.
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

    **Refund webhooks:** the eupago documentation says no webhook fires for
    refunds. **In practice it does** (confirmed live in production,
    2026-05-31): an async webhook arrives with ``method="RB:PT"``,
    ``status="REFUNDED"``, and an ``originalTrid`` field pointing back at the
    original payment's transaction_id. The SDK normalizes these via
    ``client.webhooks.parse(...)`` →
    ``WebhookEvent(method="refund", status=REFUNDED, original_transaction_id=…)``.
    The synchronous response is still authoritative (200/201 + ``refundId``),
    but the webhook is useful for reconciliation back to the original payment.
    """

    _default_auth: str = "oauth"

    def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        *,
        reason: str | None = None,
        iban: str | None = None,
        bic: str | None = None,
    ) -> PaymentResult:
        body = _build_body(amount, reason=reason, iban=iban, bic=bic)
        path = f"{_PATH_REFUND}/{transaction_id}"
        response = self._request("POST", path, json=body)
        return _parse_response(response.json(), transaction_id, amount)

    async def refund_async(
        self,
        transaction_id: str,
        amount: Decimal,
        *,
        reason: str | None = None,
        iban: str | None = None,
        bic: str | None = None,
    ) -> PaymentResult:
        body = _build_body(amount, reason=reason, iban=iban, bic=bic)
        path = f"{_PATH_REFUND}/{transaction_id}"
        response = await self._request_async("POST", path, json=body)
        return _parse_response(response.json(), transaction_id, amount)
