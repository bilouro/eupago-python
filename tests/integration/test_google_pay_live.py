"""Live ``google_pay.create_payment`` sanity check against the eupago sandbox.

Verifies the v1.02 Google Pay endpoint accepts our hosted-flow request body
(no ``googlePayToken``) and returns a valid ``redirectUrl``. A full E2E
(open the link in Chrome with a sandbox Google Pay card, complete payment,
assert webhook lands) requires a configured Google Pay test card and is
out of scope for this smoke test.

Skipped automatically unless ``EUPAGO_API_KEY`` is in the env. Skips with
a clear reason when the channel doesn't have Google Pay provisioned
(eupago returns ``BAD_REQUEST``).
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import Any

import pytest

from eupago.exceptions import ApiError

_API_KEY = os.environ.get("EUPAGO_API_KEY")

pytestmark = pytest.mark.skipif(
    not _API_KEY,
    reason="set EUPAGO_API_KEY to run live Google Pay tests",
)


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    return EupagoClient(api_key=_API_KEY or "", sandbox=True)


@pytest.mark.integration
def test_google_pay_hosted_create_returns_redirect(client: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-GP-{uuid.uuid4().hex[:10]}"
    try:
        result = client.google_pay.create_payment(
            order_id=order_id,
            amount=Decimal("1.00"),
        )
    except ApiError as e:
        if e.error_code in {"BAD_REQUEST", "INVALID_CHANNEL"}:
            pytest.skip(
                "Channel does not have Google Pay provisioned (eupago returned "
                f"{e.error_code}). Hosted-flow body shape was sent but the endpoint "
                "refuses the channel — re-run on a channel with Google Pay enabled."
            )
        raise

    assert result.status == PaymentStatus.PENDING
    assert result.transaction_id is not None
    assert result.payment_url is not None
    assert "googlepay/form/" in result.payment_url
    assert result.order_id == order_id
    assert result.amount == Decimal("1.00")
    assert result.method == "google_pay"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_google_pay_hosted_create_async(client: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-GP-A-{uuid.uuid4().hex[:10]}"
    try:
        result = await client.google_pay.create_payment_async(
            order_id=order_id,
            amount=Decimal("1.00"),
        )
    except ApiError as e:
        if e.error_code in {"BAD_REQUEST", "INVALID_CHANNEL"}:
            pytest.skip(
                f"Channel does not have Google Pay provisioned (eupago returned {e.error_code})."
            )
        raise

    assert result.status == PaymentStatus.PENDING
    assert result.transaction_id is not None
    assert result.payment_url is not None
    assert "googlepay/form/" in result.payment_url
    await client.aclose()
