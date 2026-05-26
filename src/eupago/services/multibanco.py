from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from eupago._config import LEGACY_PREFIX
from eupago.exceptions import ValidationError
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{LEGACY_PREFIX}/multibanco/create"
_PATH_INFO = f"{LEGACY_PREFIX}/multibanco/info"

_ESTADO_MAP: dict[int, PaymentStatus] = {
    0: PaymentStatus.PENDING,
}

_ESTADO_ERROR_MAP: dict[int, str] = {
    -7: "Inactive service — account lacks permission for Multibanco",
    -8: "Invalid reference",
    -9: "Invalid parameter values",
    -10: "Invalid API key",
    -11: "Payment not found",
}


def _build_create_body(
    order_id: str,
    amount: Decimal,
    *,
    expires_at: date | None = None,
    starts_at: date | None = None,
    allow_duplicate: bool = False,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    description: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    send_expiry_reminder: bool = False,
) -> dict[str, Any]:
    if amount <= 0 or amount > _MAX_AMOUNT:
        raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")

    body: dict[str, Any] = {
        "valor": float(amount),
        "id": order_id,
        "per_dup": 1 if allow_duplicate else 0,
    }

    if expires_at is not None:
        body["data_fim"] = expires_at.strftime("%Y-%m-%d")
    if starts_at is not None:
        body["data_inicio"] = starts_at.strftime("%Y-%m-%d")
    if min_amount is not None:
        body["valor_minimo"] = float(min_amount)
    if max_amount is not None:
        body["valor_maximo"] = float(max_amount)
    if email:
        body["email"] = email
    if phone_number:
        body["contacto"] = phone_number
    if send_expiry_reminder and expires_at is not None:
        body["failOver"] = "1"

    return body


def _parse_create_response(data: dict[str, Any], order_id: str, amount: Decimal) -> PaymentResult:
    estado = data.get("estado", -1)

    if isinstance(estado, int) and estado in _ESTADO_ERROR_MAP:
        from eupago.exceptions import ApiError

        raise ApiError(
            _ESTADO_ERROR_MAP[estado],
            error_code=estado,
        )

    entity = data.get("entidade")
    reference = data.get("referencia")

    return PaymentResult(
        order_id=order_id,
        amount=amount,
        entity=str(entity) if entity is not None else None,
        reference=str(reference) if reference is not None else None,
        status=PaymentStatus.PENDING,
        method="multibanco",
        raw_response=data,
    )


def _parse_info_response(data: dict[str, Any]) -> PaymentResult:
    estado = data.get("estado", -1)

    if isinstance(estado, int) and estado in _ESTADO_ERROR_MAP:
        from eupago.exceptions import ApiError

        raise ApiError(
            _ESTADO_ERROR_MAP[estado],
            error_code=estado,
        )

    entity = data.get("entidade")
    reference = data.get("referencia")
    amount_raw = data.get("valor")
    amount = Decimal(str(amount_raw)) if amount_raw is not None else None

    paid_at = data.get("data_pagamento")
    status = PaymentStatus.PAID if paid_at else PaymentStatus.PENDING

    return PaymentResult(
        order_id=data.get("id"),
        amount=amount,
        entity=str(entity) if entity is not None else None,
        reference=str(reference) if reference is not None else None,
        status=status,
        method="multibanco",
        raw_response=data,
    )


class MultibancoService(BaseService):
    _default_auth: str = "body"

    def create_reference(
        self,
        order_id: str,
        amount: Decimal,
        *,
        expires_at: date | None = None,
        starts_at: date | None = None,
        allow_duplicate: bool = False,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        description: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        send_expiry_reminder: bool = False,
    ) -> PaymentResult:
        body = _build_create_body(
            order_id,
            amount,
            expires_at=expires_at,
            starts_at=starts_at,
            allow_duplicate=allow_duplicate,
            min_amount=min_amount,
            max_amount=max_amount,
            description=description,
            email=email,
            phone_number=phone_number,
            send_expiry_reminder=send_expiry_reminder,
        )
        response = self._request("POST", _PATH_CREATE, json=body)
        return _parse_create_response(response.json(), order_id, amount)

    async def create_reference_async(
        self,
        order_id: str,
        amount: Decimal,
        *,
        expires_at: date | None = None,
        starts_at: date | None = None,
        allow_duplicate: bool = False,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        description: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        send_expiry_reminder: bool = False,
    ) -> PaymentResult:
        body = _build_create_body(
            order_id,
            amount,
            expires_at=expires_at,
            starts_at=starts_at,
            allow_duplicate=allow_duplicate,
            min_amount=min_amount,
            max_amount=max_amount,
            description=description,
            email=email,
            phone_number=phone_number,
            send_expiry_reminder=send_expiry_reminder,
        )
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_create_response(response.json(), order_id, amount)

    def get_info(
        self,
        reference: str,
        entity: str | None = None,
    ) -> PaymentResult:
        body: dict[str, Any] = {"referencia": reference}
        if entity:
            body["entidade"] = entity
        response = self._request("POST", _PATH_INFO, json=body)
        return _parse_info_response(response.json())

    async def get_info_async(
        self,
        reference: str,
        entity: str | None = None,
    ) -> PaymentResult:
        body: dict[str, Any] = {"referencia": reference}
        if entity:
            body["entidade"] = entity
        response = await self._request_async("POST", _PATH_INFO, json=body)
        return _parse_info_response(response.json())
