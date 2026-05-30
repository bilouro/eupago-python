"""End-to-end Credit Card authorize + capture against the eupago sandbox.

Flow::

    SDK authorize  ->  redirectUrl ".../formauth/<id>"
       ->  Playwright fills card form + 3DS OTP on the eupago page
       ->  SDK capture(transaction_id, amount)
       ->  webhook arrives at the AWS receiver
       ->  SDK parse_webhook validates the captured bytes (status = Paid)

**Channel capability:** the authorize endpoint requires the channel to have
*Credit Card Auth & Capture* enabled (a separate feature beyond plain Credit
Card). On a vanilla demo channel the eupago form posts to the merchant
``errorUrl`` and any subsequent capture returns ``PAYMENT_NOT_CAPTIVE`` —
when that happens the test is skipped with a clear reason rather than
failing the suite. The SDK is still exercised end-to-end (authorize body
shape, Playwright form drive, capture body shape).

Uses the official sandbox test card ``4018810000150015`` (OTP ``0101``).
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
        "set EUPAGO_API_KEY/EUPAGO_WEBHOOK_TABLE/EUPAGO_WEBHOOK_SECRET to run CC auth/capture E2E"
    ),
)

TEST_CARD = "4018810000150015"
TEST_EXPIRY = "12/30"
TEST_CVV = "123"
TEST_NAME = "Test User"
TEST_OTP_SUCCESS = "0101"

_ERR_PATH = "/err"
_OK_PATH = "/ok"


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
    """Authorize forces 3DS for every amount on this sandbox channel, so we
    always drive the ACS challenge. Mirrors the helper in test_credit_card_3ds.
    """
    try:
        page.wait_for_url("**x3d-sim.credorax.net/acs/challenge**", timeout=15_000)
    except pw.TimeoutError:
        return  # no 3DS branch this time, nothing to do
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
def test_credit_card_authorize_then_capture(client: Any, browser: Any, table: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-CCAC-{uuid.uuid4().hex[:10]}"
    amount = Decimal("100.00")
    auth = client.credit_card.authorize(
        order_id=order_id,
        amount=amount,
        success_url=f"{_RETURN_BASE}{_OK_PATH}",
        error_url=f"{_RETURN_BASE}{_ERR_PATH}",
        back_url=f"{_RETURN_BASE}/back",
    )
    assert auth.payment_url is not None
    assert "formauth/" in auth.payment_url
    assert auth.transaction_id is not None

    page = browser.new_page()
    final_url = ""
    try:
        page.goto(auth.payment_url, wait_until="networkidle", timeout=30_000)
        _fill_card_form(page)
        _fill_otp_if_needed(page)
        page.wait_for_url(
            lambda url: (
                "creditcard/formauth/" not in url
                and "x3d-sim.credorax.net" not in url
                and "credorax.net/eupago" not in url
            ),
            timeout=60_000,
        )
        final_url = page.url
    finally:
        page.close()

    if final_url.endswith(_ERR_PATH) or _ERR_PATH + "?" in final_url:
        pytest.skip(
            "Credit Card channel does not have Auth & Capture enabled — "
            "the 3DS form posted to the merchant errorUrl. The SDK still "
            "exercised authorize + form drive; capture requires the channel "
            "feature to be provisioned by eupago."
        )

    try:
        captured = client.credit_card.capture(
            transaction_id=auth.transaction_id,
            amount=amount,
            success_url=f"{_RETURN_BASE}{_OK_PATH}",
            error_url=f"{_RETURN_BASE}{_ERR_PATH}",
            back_url=f"{_RETURN_BASE}/back",
        )
    except ApiError as e:
        if e.error_code == "PAYMENT_NOT_CAPTIVE":
            pytest.skip(
                "eupago refused capture with PAYMENT_NOT_CAPTIVE — the demo "
                "channel does not have Credit Card Auth & Capture provisioned."
            )
        raise

    assert captured.status in (PaymentStatus.PAID, PaymentStatus.PENDING)

    item = _wait_for_webhook(table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "credit_card"
