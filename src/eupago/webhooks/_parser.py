from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from eupago.models.payment import normalize_method, normalize_status
from eupago.models.webhook import WebhookEvent


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_v1(params: dict[str, str]) -> WebhookEvent:
    method_raw = params.get("mp", "")
    return WebhookEvent(
        order_id=params.get("identificador"),
        transaction_id=params.get("transacao"),
        reference=params.get("referencia"),
        entity=params.get("entidade"),
        amount=_safe_decimal(params.get("valor")),
        status=normalize_status(params.get("status", "Paid")),
        method=normalize_method(method_raw) if method_raw else None,
        paid_at=params.get("data"),
        channel=params.get("canal"),
        fee=_safe_decimal(params.get("comissao")),
    )


def parse_v2(body: dict[str, Any]) -> WebhookEvent:
    # Real eupago v2.0 wraps fields in "transaction" (singular); keep "transactions"
    # and the bare body as fallbacks.
    tx = body.get("transaction") or body.get("transactions") or body
    amount_obj = tx.get("amount", {})
    fees_obj = tx.get("fees", {})
    channel = body.get("channel", {})

    method_raw = tx.get("method", "")
    status_raw = tx.get("status", "Paid")

    return WebhookEvent(
        order_id=tx.get("identifier"),
        transaction_id=str(tx["trid"]) if "trid" in tx else None,
        # Refund webhooks (method="RB:PT") carry the original payment's trid
        # in ``originalTrid`` — confirmed live in production 2026-05-31.
        original_transaction_id=(
            str(tx["originalTrid"]) if tx.get("originalTrid") is not None else None
        ),
        reference=str(tx["reference"]) if "reference" in tx else None,
        entity=str(tx["entity"]) if "entity" in tx else None,
        amount=_safe_decimal(
            amount_obj.get("value") if isinstance(amount_obj, dict) else amount_obj
        ),
        currency=(amount_obj.get("currency", "EUR") if isinstance(amount_obj, dict) else "EUR"),
        status=normalize_status(status_raw),
        method=normalize_method(method_raw) if method_raw else None,
        paid_at=tx.get("date"),
        channel=channel.get("name") if isinstance(channel, dict) else None,
        fee=_safe_decimal(fees_obj.get("value") if isinstance(fees_obj, dict) else None),
    )


def parse_body(raw_body: bytes) -> dict[str, Any]:
    return json.loads(raw_body)  # type: ignore[no-any-return]
