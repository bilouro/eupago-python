from __future__ import annotations

from decimal import Decimal

from eupago.models.payment import (
    PaymentResult,
    PaymentStatus,
    normalize_method,
    normalize_status,
)
from eupago.models.webhook import WebhookEvent


def test_normalize_status_string() -> None:
    assert normalize_status("Paid") == PaymentStatus.PAID
    assert normalize_status("paga") == PaymentStatus.PAID
    assert normalize_status("Expired") == PaymentStatus.EXPIRED
    assert normalize_status("Cancel") == PaymentStatus.CANCELLED
    assert normalize_status("unknown") == PaymentStatus.PENDING


def test_normalize_status_int() -> None:
    assert normalize_status(0) == PaymentStatus.PENDING
    assert normalize_status(-10) == PaymentStatus.ERROR


def test_normalize_method() -> None:
    assert normalize_method("MW:PT") == "mbway"
    assert normalize_method("PC:PT") == "multibanco"
    assert normalize_method("Mbway") == "mbway"
    assert normalize_method("UNKNOWN") == "unknown"


def test_payment_result_defaults() -> None:
    result = PaymentResult()
    assert result.currency == "EUR"
    assert result.status == PaymentStatus.PENDING
    assert result.amount is None


def test_payment_result_with_decimal_amount() -> None:
    result = PaymentResult(amount=Decimal("49.90"), order_id="ORD-1")
    assert result.amount == Decimal("49.90")
    assert result.order_id == "ORD-1"


def test_webhook_event_defaults() -> None:
    event = WebhookEvent()
    assert event.status == PaymentStatus.PAID
    assert event.currency == "EUR"
