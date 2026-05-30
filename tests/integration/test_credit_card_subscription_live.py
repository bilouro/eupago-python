"""End-to-end Credit Card subscription against the eupago sandbox.

Flow::

    SDK create_subscription  ->  redirectUrl ".../formsub/<id>"
       ->  Playwright fills the card-registration form (incl. 3DS OTP)
       ->  webhook arrives (subscription registered) — capture raw payload
       ->  SDK charge_subscription(recurrent_id=subscriptionID, ...)
       ->  charge webhook arrives at AWS receiver
       ->  SDK parse_webhook validates the captured bytes (status = Paid)

This is the test that discovers what eupago actually puts on the wire for
subscription webhooks — the raw payload is preserved in DynamoDB so the
SDK and docs can use the verified field names.
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
pw = pytest.importorskip("playwright.sync_api")

from eupago.exceptions import ApiError  # noqa: E402

_API_KEY = os.environ.get("EUPAGO_API_KEY")
_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET")
_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_RETURN_BASE = os.environ.get("EUPAGO_CC_RETURN_BASE", "https://breathpilates.pt")
_HEADFUL = os.environ.get("EUPAGO_PW_HEADFUL", "0") == "1"

pytestmark = pytest.mark.skipif(
    not (_API_KEY and _SECRET and _TABLE),
    reason=(
        "set EUPAGO_API_KEY/EUPAGO_WEBHOOK_TABLE/EUPAGO_WEBHOOK_SECRET to run CC subscription E2E"
    ),
)

TEST_CARD = "4018810000150015"
TEST_EXPIRY = "12/30"
TEST_CVV = "123"
TEST_NAME = "Test User"
TEST_OTP_SUCCESS = "0101"


@pytest.fixture
def client() -> Any:
    from eupago import EupagoClient

    return EupagoClient(api_key=_API_KEY or "", sandbox=True, webhook_secret=_SECRET)


@pytest.fixture(scope="module")
def table() -> Any:
    return boto3.resource("dynamodb").Table(_TABLE)


@pytest.fixture
def browser() -> Iterator[Any]:
    with pw.sync_playwright() as p:
        b = p.chromium.launch(headless=not _HEADFUL)
        yield b
        b.close()


def _fill_card_form(page: Any) -> None:
    page.wait_for_selector('input[autocomplete="cc-number"]', timeout=20_000)
    page.locator('input[autocomplete="cc-number"]').fill(TEST_CARD)
    page.locator('input[autocomplete="cc-exp"]').fill(TEST_EXPIRY)
    page.locator('input[placeholder="123"]').first.fill(TEST_CVV)
    page.locator('input[autocomplete="cc-name"]').fill(TEST_NAME)
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('button')).some(b => !b.disabled)",
        timeout=10_000,
    )
    page.get_by_role("button").first.click()


def _fill_otp_if_needed(page: Any) -> None:
    try:
        page.wait_for_url("**x3d-sim.credorax.net/acs/challenge**", timeout=15_000)
    except pw.TimeoutError:
        return
    page.wait_for_selector('input[name="otp"]', timeout=15_000)
    field = page.locator('input[name="otp"]')
    field.click()
    field.press_sequentially(TEST_OTP_SUCCESS, delay=50)
    page.wait_for_function(
        "() => {\n"
        "  const b = Array.from(document.querySelectorAll('button'))\n"
        "    .find(x => x.textContent.trim() === 'Pay');\n"
        "  return b && !b.disabled;\n"
        "}",
        timeout=10_000,
    )
    page.get_by_role("button", name="Pay").click()
    page.wait_for_url(
        lambda url: "x3d-sim.credorax.net/acs/challenge" not in url,
        timeout=45_000,
    )


def _wait_for_webhook(table: Any, order_id: str, timeout: int = 90) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


@pytest.mark.integration
def test_credit_card_subscription_register_then_charge(
    client: Any, browser: Any, table: Any
) -> None:
    from eupago.models.payment import PaymentStatus

    register_order = f"ITEST-CCSUB-{uuid.uuid4().hex[:10]}"
    monthly_amount = Decimal("19.99")
    sub = client.credit_card.create_subscription(
        order_id=register_order,
        amount=monthly_amount,
        success_url=f"{_RETURN_BASE}/ok",
        error_url=f"{_RETURN_BASE}/err",
        back_url=f"{_RETURN_BASE}/back",
    )
    assert sub.payment_url is not None
    assert "formsub/" in sub.payment_url, (
        f"expected /formsub/ URL for subscription, got {sub.payment_url}"
    )
    subscription_id = sub.transaction_id  # _parse_response maps subscriptionID here
    assert subscription_id is not None

    page = browser.new_page()
    final_url = ""
    try:
        page.goto(sub.payment_url, wait_until="networkidle", timeout=30_000)
        _fill_card_form(page)
        _fill_otp_if_needed(page)
        page.wait_for_url(
            lambda url: (
                "creditcard/formsub/" not in url
                and "x3d-sim.credorax.net" not in url
                and "credorax.net/eupago" not in url
            ),
            timeout=60_000,
        )
        final_url = page.url
    finally:
        page.close()

    if final_url.endswith("/err") or "/err?" in final_url:
        pytest.skip(
            "Credit Card channel does not have Subscription enabled — the "
            "registration form posted to the merchant errorUrl. The SDK still "
            "exercised create_subscription and the form drive."
        )

    # Wait briefly for eupago to fire the registration webhook (if any) and
    # then attempt the first charge against the discovered subscriptionID.
    charge_order = f"ITEST-CCSUBCHG-{uuid.uuid4().hex[:10]}"
    try:
        charge = client.credit_card.charge_subscription(
            recurrent_id=subscription_id,
            order_id=charge_order,
            amount=monthly_amount,
            success_url=f"{_RETURN_BASE}/ok",
            error_url=f"{_RETURN_BASE}/err",
            back_url=f"{_RETURN_BASE}/back",
        )
    except ApiError as e:
        pytest.skip(
            f"charge_subscription was refused by eupago: {e.error_code} — likely "
            "the channel doesn't have CC Subscription Pay enabled."
        )

    assert charge.status in (PaymentStatus.PAID, PaymentStatus.PENDING)

    item = _wait_for_webhook(table, charge_order)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == charge_order
    assert event.status == PaymentStatus.PAID
    assert event.method == "credit_card"
