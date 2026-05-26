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
    tx = body.get("transactions", body)
    amount_obj = tx.get("amount", {})

    method_raw = tx.get("method", "")
    status_raw = tx.get("status", "Paid")

    return WebhookEvent(
        order_id=tx.get("identifier"),
        transaction_id=str(tx["trid"]) if "trid" in tx else None,
        reference=str(tx["reference"]) if "reference" in tx else None,
        entity=str(tx["entity"]) if "entity" in tx else None,
        amount=_safe_decimal(
            amount_obj.get("value") if isinstance(amount_obj, dict) else amount_obj
        ),
        currency=(amount_obj.get("currency", "EUR") if isinstance(amount_obj, dict) else "EUR"),
        status=normalize_status(status_raw),
        method=normalize_method(method_raw) if method_raw else None,
        paid_at=tx.get("date"),
        channel=(
            body.get("channel", {}).get("name") if isinstance(body.get("channel"), dict) else None
        ),
        fee=_safe_decimal(
            body.get("transactions", {}).get("fees", {}).get("value")
            if isinstance(body.get("transactions", {}).get("fees"), dict)
            else None
        ),
    )


def parse_body(raw_body: bytes) -> dict[str, Any]:
    return json.loads(raw_body)  # type: ignore[no-any-return]
