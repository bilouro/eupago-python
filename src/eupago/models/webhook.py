from __future__ import annotations

from decimal import Decimal

from eupago.models._base import BaseModel
from eupago.models.payment import PaymentStatus


class WebhookEvent(BaseModel):
    order_id: str | None = None
    transaction_id: str | None = None
    # Set on refund webhooks (method = ``"refund"``): the trid of the original
    # paid transaction being refunded. Lets you correlate the refund back to
    # the original payment without keeping your own mapping.
    original_transaction_id: str | None = None
    reference: str | None = None
    entity: str | None = None
    amount: Decimal | None = None
    currency: str = "EUR"
    status: PaymentStatus = PaymentStatus.PAID
    method: str | None = None
    paid_at: str | None = None
    channel: str | None = None
    fee: Decimal | None = None
