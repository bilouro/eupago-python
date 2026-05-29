"""Live ``credit_card.create_payment`` sanity check against the eupago sandbox.

Verifies the SDK builds a valid v1.02 request body (amount object, all three
return URLs, header auth) and parses the real response shape — without
walking the 3D-Secure form. Driving the form with the official test card
``4018810000150015`` (OTP ``0101``) is a future Playwright job; this test
just guarantees we reach a ``Success`` redirectUrl.

Skipped automatically unless ``EUPAGO_API_KEY`` is in the env.
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import Any

import pytest

_API_KEY = os.environ.get("EUPAGO_API_KEY")
_RETURN_BASE = os.environ.get("EUPAGO_CC_RETURN_BASE", "https://breathpilates.pt")

pytestmark = pytest.mark.skipif(
    not _API_KEY,
    reason="set EUPAGO_API_KEY to run live credit card tests",
)


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    return EupagoClient(api_key=_API_KEY or "", sandbox=True)


@pytest.mark.integration
def test_credit_card_create_returns_redirect(client: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-CC-{uuid.uuid4().hex[:10]}"
    result = client.credit_card.create_payment(
        order_id=order_id,
        amount=Decimal("600.00"),  # > 500 EUR triggers the OTP prompt at the form
        success_url=f"{_RETURN_BASE}/ok",
        error_url=f"{_RETURN_BASE}/err",
        back_url=f"{_RETURN_BASE}/back",
    )

    assert result.status == PaymentStatus.PENDING
    assert result.transaction_id is not None
    assert result.reference is not None
    assert result.payment_url is not None
    assert "creditcard/form/" in result.payment_url
    assert result.order_id == order_id
    assert result.amount == Decimal("600.00")
    assert result.method == "credit_card"
