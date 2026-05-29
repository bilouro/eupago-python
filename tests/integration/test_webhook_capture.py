"""End-to-end paid-flow integration tests against the eupago sandbox.

What each test does in one breath::

    SDK creates the payment  ->  helper marks it Paga in the backoffice
       ->  eupago fires the webhook  ->  our AWS receiver captures it
       ->  SDK parse_webhook validates the captured bytes (signature + parsing)

Requires:
- the AWS receiver from ``tests/integration/infra`` deployed,
- the eupago sandbox channel pointing its Webhook 2.0 URL at the receiver,
- env vars ``EUPAGO_API_KEY``, ``EUPAGO_WEBHOOK_TABLE``, ``EUPAGO_WEBHOOK_SECRET``,
  ``EUPAGO_BACKOFFICE_EMAIL``, ``EUPAGO_BACKOFFICE_PASSWORD``,
  AWS credentials for the table.

Run deliberately::

    pytest -m integration tests/integration/test_webhook_capture.py -s

A single ``BackofficeSession`` is opened for the whole module (one login) and
torn down at the end — so we don't login/approve for every test.
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
    not (_TABLE and _API_KEY and _BO_EMAIL and _BO_PASS),
    reason=(
        "set EUPAGO_WEBHOOK_TABLE / EUPAGO_API_KEY / "
        "EUPAGO_BACKOFFICE_EMAIL / EUPAGO_BACKOFFICE_PASSWORD to run live tests"
    ),
)


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    # Function-scoped because the async transport binds to the test's event loop;
    # sharing across tests trips RuntimeError on teardown in py3.14.
    return EupagoClient(api_key=_API_KEY or "", sandbox=True, webhook_secret=_SECRET)


@pytest.fixture(scope="module")
def backoffice() -> Iterator[BackofficeSession]:
    with BackofficeSession(_BO_EMAIL or "", _BO_PASS or "") as s:
        yield s


@pytest.fixture(scope="module")
def table() -> Any:
    return boto3.resource("dynamodb").Table(_TABLE)


def _wait_for_webhook(client: Any, table: Any, order_id: str, timeout: int = 60) -> dict[str, Any]:
    """Find the captured webhook for ``order_id``.

    Fast path: the cleartext Lambda keys items by the eupago ``identifier`` so
    a direct GetItem hits. Encrypted webhooks land as ``raw-<uuid>`` (the Lambda
    can't read the identifier from ciphertext), so we fall back to scanning
    recent items and matching via decrypt+parse.
    """
    deadline = time.time() + timeout
    floor = int(time.time()) - 90  # only look at recently captured items
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        for it in table.scan()["Items"]:
            if int(it.get("received_at", 0)) < floor:
                continue
            if not str(it.get("order_id", "")).startswith("raw-"):
                continue
            try:
                event = client.webhooks.parse(
                    body=it["raw_body"], headers=json.loads(it["headers"])
                )
            except Exception:  # noqa: S112 - bad signature/decrypt on unrelated items is expected
                continue
            if event.order_id == order_id:
                return it  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


def _new_order_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.mark.integration
def test_multibanco_paid_flow(client: Any, backoffice: BackofficeSession, table: Any) -> None:
    order_id = _new_order_id("ITEST-MB")
    ref = client.multibanco.create_reference(order_id=order_id, amount=Decimal("1.23"))
    assert ref.reference is not None

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(client, table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.reference == ref.reference
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "multibanco"

    paid = client.multibanco.get_info(reference=ref.reference, entity=ref.entity)
    assert paid.status == PaymentStatus.PAID
    assert paid.amount == Decimal("1.23000")
    assert paid.order_id == order_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multibanco_async_paid_flow(
    client: Any, backoffice: BackofficeSession, table: Any
) -> None:
    order_id = _new_order_id("ITEST-MBA")
    ref = await client.multibanco.create_reference_async(order_id=order_id, amount=Decimal("2.34"))

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(client, table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.reference == ref.reference
    assert event.status == PaymentStatus.PAID

    paid = await client.multibanco.get_info_async(reference=ref.reference, entity=ref.entity)
    assert paid.status == PaymentStatus.PAID


@pytest.mark.integration
def test_mbway_paid_flow(client: Any, backoffice: BackofficeSession, table: Any) -> None:
    order_id = _new_order_id("ITEST-MW")
    result = client.mbway.create_payment(
        order_id=order_id, amount=Decimal("3.45"), phone_number="912345678"
    )
    assert result.transaction_id is not None

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(client, table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "mbway"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mbway_async_paid_flow(
    client: Any, backoffice: BackofficeSession, table: Any
) -> None:
    order_id = _new_order_id("ITEST-MWA")
    await client.mbway.create_payment_async(
        order_id=order_id, amount=Decimal("4.56"), phone_number="912345678"
    )

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(client, table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "mbway"
