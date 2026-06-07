"""End-to-end Refund against the eupago sandbox.

Flow::

    SDK mbway.create_payment   ->  backoffice mark-paid
       ->  webhook (PAID) lands at AWS receiver  ->  SDK parses, extracts trid
       ->  SDK refunds.refund(trid, amount, reason=...) via management API
       ->  assert HTTP 201 + refundId + status REFUNDED

**Auth picker.** The Management API can be authenticated either with proper
OAuth (``EUPAGO_CLIENT_ID`` + ``EUPAGO_CLIENT_SECRET`` — eupago now issues
these self-service in the backoffice as of 2026-06) or with the backoffice
login Bearer (``EUPAGO_BACKOFFICE_EMAIL`` + ``EUPAGO_BACKOFFICE_PASSWORD``,
the original escape hatch). This module prefers OAuth when both sets are
available, falls back to the bearer otherwise. Production callers should
always prefer OAuth.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest

boto3 = pytest.importorskip("boto3")

from eupago.models.payment import PaymentStatus  # noqa: E402

from .sandbox_backoffice import BackofficeSession  # noqa: E402

_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_API_KEY = os.environ.get("EUPAGO_API_KEY")
_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET")
_BO_EMAIL = os.environ.get("EUPAGO_BACKOFFICE_EMAIL")
_BO_PASS = os.environ.get("EUPAGO_BACKOFFICE_PASSWORD")
_CLIENT_ID = os.environ.get("EUPAGO_CLIENT_ID")
_CLIENT_SECRET = os.environ.get("EUPAGO_CLIENT_SECRET")

# Need API key + webhook secret + DDB table to drive any flow at all, and
# at least one Management API auth path (OAuth or backoffice login).
_BASE_OK = bool(_TABLE and _API_KEY and _SECRET)
_OAUTH_OK = bool(_CLIENT_ID and _CLIENT_SECRET)
_BO_OK = bool(_BO_EMAIL and _BO_PASS)
# Backoffice creds are also needed to mark-paid even when OAuth is the auth
# path — the mark-paid step doesn't go through /api/management/*.
_NEED_BO = True

pytestmark = pytest.mark.skipif(
    not (_BASE_OK and _BO_OK and (_OAUTH_OK or _BO_OK)),
    reason=(
        "set EUPAGO_API_KEY / EUPAGO_WEBHOOK_TABLE / EUPAGO_WEBHOOK_SECRET, "
        "EUPAGO_BACKOFFICE_EMAIL/PASSWORD (for mark-paid), and ideally "
        "EUPAGO_CLIENT_ID/SECRET (OAuth) to run live refund tests"
    ),
)


@pytest.fixture(scope="module")
def backoffice() -> Iterator[BackofficeSession]:
    with BackofficeSession(_BO_EMAIL or "", _BO_PASS or "") as s:
        yield s


@pytest.fixture(scope="module")
def table() -> Any:
    return boto3.resource("dynamodb").Table(_TABLE)


@pytest.fixture
def client_with_mgmt_auth(backoffice: BackofficeSession) -> Any:
    """Build an EupagoClient with Management API auth wired.

    Prefers OAuth (production-grade). Falls back to the backoffice login
    Bearer when OAuth env vars are absent. The chosen mode is logged via
    `print()` so the test output makes it obvious which path was taken.
    """
    from eupago import EupagoClient

    if _OAUTH_OK:
        print("\n[auth] using OAuth client_credentials")
        return EupagoClient(
            api_key=_API_KEY or "",
            sandbox=True,
            webhook_secret=_SECRET,
            client_id=_CLIENT_ID,
            client_secret=_CLIENT_SECRET,
        )

    print("\n[auth] using backoffice login bearer (no OAuth env)")
    return EupagoClient(
        api_key=_API_KEY or "",
        sandbox=True,
        webhook_secret=_SECRET,
        management_bearer=backoffice._bearer,
    )


def _wait_for_webhook(table: Any, order_id: str, timeout: int = 60) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


@pytest.mark.integration
def test_refund_paid_mbway(
    client_with_mgmt_auth: Any, backoffice: BackofficeSession, table: Any
) -> None:
    """Pay an MB WAY transaction, then refund it — full SDK roundtrip.

    We use MB WAY (not Multibanco) because eupago's refund endpoint requires
    an ``iban`` for Multibanco refunds (bank-to-bank settlement), while
    MB WAY refunds settle wallet-to-wallet and do not.
    """
    order_id = f"ITEST-REF-{uuid.uuid4().hex[:10]}"
    amount = Decimal("1.50")

    result = client_with_mgmt_auth.mbway.create_payment(
        order_id=order_id, amount=amount, phone_number="912345678"
    )
    assert result.transaction_id is not None

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(table, order_id)
    event = client_with_mgmt_auth.webhooks.parse(
        body=item["raw_body"], headers=json.loads(item["headers"])
    )
    assert event.status == PaymentStatus.PAID
    assert event.transaction_id is not None

    refund = client_with_mgmt_auth.refunds.refund(
        transaction_id=event.transaction_id,
        amount=amount,
        reason="SDK live verification",
    )

    assert refund.status == PaymentStatus.REFUNDED, (
        f"unexpected refund status: {refund.status}, raw={refund.raw_response}"
    )
    # The eupago refund response carries refundId — preserved in raw_response
    # because PaymentResult is shared across payment kinds.
    assert "refundId" in refund.raw_response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refund_paid_mbway_async(
    client_with_mgmt_auth: Any, backoffice: BackofficeSession, table: Any
) -> None:
    order_id = f"ITEST-REF-A-{uuid.uuid4().hex[:10]}"
    amount = Decimal("2.50")

    await client_with_mgmt_auth.mbway.create_payment_async(
        order_id=order_id, amount=amount, phone_number="912345678"
    )
    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(table, order_id)
    event = client_with_mgmt_auth.webhooks.parse(
        body=item["raw_body"], headers=json.loads(item["headers"])
    )
    assert event.transaction_id is not None

    refund = await client_with_mgmt_auth.refunds.refund_async(
        transaction_id=event.transaction_id,
        amount=amount,
        reason="SDK live verification (async)",
    )
    assert refund.status == PaymentStatus.REFUNDED
    await client_with_mgmt_auth.aclose()
