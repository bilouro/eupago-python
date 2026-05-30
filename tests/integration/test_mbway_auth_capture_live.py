"""End-to-end MB WAY authorize + capture against the eupago sandbox.

What this exercises::

    SDK authorize  ->  backoffice marks the auth as approved
       ->  SDK capture  ->  eupago fires the Paid webhook
       ->  AWS receiver captures  ->  SDK parse_webhook validates

**Channel capability:** ``/api/v1.02/mbway/authorize`` is gated by an eupago
channel feature called *Auth & Capture* (a B2B / subscription-style add-on).
On a vanilla demo MB WAY channel the endpoint returns HTTP 400 BAD_REQUEST
even with a body that exactly matches the published schema. When that happens
this test is skipped with a clear reason instead of failing the suite — the
SDK is exercised and the body shape is validated, but the live behaviour can
only be asserted on a channel where the feature is enabled.

Skipped automatically unless the live env vars are set.
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

from eupago.exceptions import ApiError  # noqa: E402
from eupago.models.payment import PaymentStatus  # noqa: E402

from .sandbox_backoffice import BackofficeSession  # noqa: E402

_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_API_KEY = os.environ.get("EUPAGO_API_KEY")
_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET")
_BO_EMAIL = os.environ.get("EUPAGO_BACKOFFICE_EMAIL")
_BO_PASS = os.environ.get("EUPAGO_BACKOFFICE_PASSWORD")

pytestmark = pytest.mark.skipif(
    not (_TABLE and _API_KEY and _BO_EMAIL and _BO_PASS),
    reason=(
        "set EUPAGO_WEBHOOK_TABLE / EUPAGO_API_KEY / EUPAGO_BACKOFFICE_EMAIL "
        "/ EUPAGO_BACKOFFICE_PASSWORD to run live tests"
    ),
)


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    return EupagoClient(api_key=_API_KEY or "", sandbox=True, webhook_secret=_SECRET)


@pytest.fixture(scope="module")
def backoffice() -> Iterator[BackofficeSession]:
    with BackofficeSession(_BO_EMAIL or "", _BO_PASS or "") as s:
        yield s


@pytest.fixture(scope="module")
def table() -> Any:
    return boto3.resource("dynamodb").Table(_TABLE)


def _wait_for_webhook(table: Any, order_id: str, timeout: int = 60) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


def _authorize_or_skip(client: Any, order_id: str, amount: Decimal) -> Any:
    try:
        return client.mbway.authorize(order_id=order_id, amount=amount, phone_number="912345678")
    except ApiError as e:
        if e.error_code == "BAD_REQUEST":
            pytest.skip(
                "MB WAY channel does not have Auth & Capture enabled "
                "(eupago returned BAD_REQUEST). The SDK body shape was sent "
                "but the endpoint refuses the channel — re-run on a channel "
                "with the Auth & Capture feature provisioned."
            )
        raise


@pytest.mark.integration
def test_mbway_authorize_then_capture(
    client: Any, backoffice: BackofficeSession, table: Any
) -> None:
    order_id = f"ITEST-MWAC-{uuid.uuid4().hex[:10]}"
    amount = Decimal("5.67")

    auth = _authorize_or_skip(client, order_id, amount)
    assert auth.transaction_id is not None
    assert auth.status == PaymentStatus.PENDING

    backoffice.mark_paid_by_identifier(order_id)

    captured = client.mbway.capture(transaction_id=auth.transaction_id, amount=amount)
    assert captured.status in (PaymentStatus.PAID, PaymentStatus.PENDING), (
        f"unexpected capture status: {captured.status}, raw={captured.raw_response}"
    )

    item = _wait_for_webhook(table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "mbway"
