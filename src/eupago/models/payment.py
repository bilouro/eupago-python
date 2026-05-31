from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from eupago.models._base import BaseModel


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ERROR = "error"
    DECLINED = "declined"


EUPAGO_STATUS_MAP: dict[str, PaymentStatus] = {
    "Paid": PaymentStatus.PAID,
    "paga": PaymentStatus.PAID,
    "Reembolsado": PaymentStatus.REFUNDED,
    "Refund": PaymentStatus.REFUNDED,
    "reembolsada": PaymentStatus.REFUNDED,
    # eupago uses US spelling "Canceled" (single L) in webhooks — confirmed
    # live for MB WAY rejected-by-customer transactions in 2026.
    "Canceled": PaymentStatus.CANCELLED,
    "Cancelled": PaymentStatus.CANCELLED,
    "Cancel": PaymentStatus.CANCELLED,
    "cancelada": PaymentStatus.CANCELLED,
    "Expired": PaymentStatus.EXPIRED,
    "expirada": PaymentStatus.EXPIRED,
    "Error": PaymentStatus.ERROR,
    "erro": PaymentStatus.ERROR,
    "Pending": PaymentStatus.PENDING,
    "pendente": PaymentStatus.PENDING,
    "Pendente": PaymentStatus.PENDING,
}

EUPAGO_METHOD_MAP: dict[str, str] = {
    "MW:PT": "mbway",
    "PC:PT": "multibanco",
    "PS:PT": "payshop",
    "CC:PT": "credit_card",
    "PF:PT": "paysafecard",
    "DD:PT": "direct_debit",
    "CP:PT": "cofidis",
    "GP:PT": "google_pay",
    "PA:PT": "apple_pay",
    "PX:PT": "pix",
    "FP:PT": "floa",
    "Multibanco": "multibanco",
    "Mbway": "mbway",
    "CreditCard": "credit_card",
    "Pix": "pix",
    "GooglePay": "google_pay",
    "ApplePay": "apple_pay",
}


def normalize_status(raw: str | int) -> PaymentStatus:
    if isinstance(raw, int):
        if raw == 0:
            return PaymentStatus.PENDING
        return PaymentStatus.ERROR
    return EUPAGO_STATUS_MAP.get(raw, PaymentStatus.PENDING)


def normalize_method(raw: str) -> str:
    return EUPAGO_METHOD_MAP.get(raw, raw.lower())


class PaymentResult(BaseModel):
    order_id: str | None = None
    amount: Decimal | None = None
    currency: str = "EUR"
    transaction_id: str | None = None
    reference: str | None = None
    entity: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    payment_url: str | None = None
    method: str | None = None
    raw_response: dict[str, Any] | None = None
