"""End-to-end Refund against the eupago sandbox.

Flow::

    SDK multibanco.create_reference  ->  backoffice mark-paid
       ->  webhook (PAID) lands at AWS receiver  ->  SDK parses, extracts trid
       ->  SDK refunds.refund(trid, amount, reason=...) via management API
       ->  assert HTTP 201 + refundId + status REFUNDED

**Auth shortcut for tests:** eupago issues OAuth ``client_id`` /
``client_secret`` for ``/api/management/*`` on request via support, not in
the backoffice. While we wait for those creds we use the alternative
Bearer that ``/api/auth/login`` (the backoffice login endpoint) returns —
the same token the backoffice itself uses to call the management API. The
SDK exposes this via ``EupagoClient(management_bearer=...)`` so the test
can drive the real refund endpoint with the right body shape.

Production callers should still prefer OAuth via ``client_id``/
``client_secret``; the bearer-injection path is an escape hatch.
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

pytestmark = pytest.mark.skipif(
    not (_TABLE and _API_KEY and _SECRET and _BO_EMAIL and _BO_PASS),
    reason=(
        "set EUPAGO_API_KEY/EUPAGO_WEBHOOK_TABLE/EUPAGO_WEBHOOK_SECRET/"
        "EUPAGO_BACKOFFICE_* to run live refund tests"
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
def client_with_bearer(backoffice: BackofficeSession) -> Any:
    from eupago import EupagoClient

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
def test_refund_paid_mbway_via_backoffice_bearer(
    client_with_bearer: Any, backoffice: BackofficeSession, table: Any
) -> None:
    """Pay an MB WAY transaction, then refund it — full SDK roundtrip.

    We use MB WAY (not Multibanco) because eupago's refund endpoint requires
    an ``iban`` for Multibanco refunds (bank-to-bank settlement), while
    MB WAY refunds settle wallet-to-wallet and do not.
    """
    order_id = f"ITEST-REF-{uuid.uuid4().hex[:10]}"
    amount = Decimal("1.50")

    result = client_with_bearer.mbway.create_payment(
        order_id=order_id, amount=amount, phone_number="912345678"
    )
    assert result.transaction_id is not None

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(table, order_id)
    event = client_with_bearer.webhooks.parse(
        body=item["raw_body"], headers=json.loads(item["headers"])
    )
    assert event.status == PaymentStatus.PAID
    assert event.transaction_id is not None

    refund = client_with_bearer.refunds.refund(
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
    client_with_bearer: Any, backoffice: BackofficeSession, table: Any
) -> None:
    order_id = f"ITEST-REF-A-{uuid.uuid4().hex[:10]}"
    amount = Decimal("2.50")

    await client_with_bearer.mbway.create_payment_async(
        order_id=order_id, amount=amount, phone_number="912345678"
    )
    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(table, order_id)
    event = client_with_bearer.webhooks.parse(
        body=item["raw_body"], headers=json.loads(item["headers"])
    )
    assert event.transaction_id is not None

    refund = await client_with_bearer.refunds.refund_async(
        transaction_id=event.transaction_id,
        amount=amount,
        reason="SDK live verification (async)",
    )
    assert refund.status == PaymentStatus.REFUNDED
    await client_with_bearer.aclose()
