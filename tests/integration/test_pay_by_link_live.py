"""Live ``pay_by_link.create_payment`` sanity check against the eupago sandbox.

Verifies the v1.02 PayByLink endpoint accepts our request body and returns a
valid ``redirectUrl``. A full E2E (open the link, pick a method, complete
payment, assert webhook lands) would require Playwright + a payment method
the sandbox supports headlessly — out of scope for this smoke test.

Skipped automatically unless ``EUPAGO_API_KEY`` is in the env.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

_API_KEY = os.environ.get("EUPAGO_API_KEY")

pytestmark = pytest.mark.skipif(
    not _API_KEY,
    reason="set EUPAGO_API_KEY to run live Pay By Link tests",
)


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    return EupagoClient(api_key=_API_KEY or "", sandbox=True)


@pytest.mark.integration
def test_pay_by_link_create_returns_redirect(client: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-PBL-{uuid.uuid4().hex[:10]}"
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    result = client.pay_by_link.create_payment(
        order_id=order_id,
        amount=Decimal("49.90"),
        expires_at=expires.replace(tzinfo=None),
    )

    assert result.status == PaymentStatus.PENDING
    assert result.transaction_id is not None
    assert result.payment_url is not None
    assert "paybylink/form/" in result.payment_url
    assert result.order_id == order_id
    assert result.amount == Decimal("49.90")
    assert result.method == "pay_by_link"
