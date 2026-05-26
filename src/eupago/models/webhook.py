from __future__ import annotations

from decimal import Decimal

from eupago.models._base import BaseModel
from eupago.models.payment import PaymentStatus


class WebhookEvent(BaseModel):
    order_id: str | None = None
    transaction_id: str | None = None
    reference: str | None = None
    entity: str | None = None
    amount: Decimal | None = None
    currency: str = "EUR"
    status: PaymentStatus = PaymentStatus.PAID
    method: str | None = None
    paid_at: str | None = None
    channel: str | None = None
    fee: Decimal | None = None
