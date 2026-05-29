"""End-to-end credit card test via Playwright.

Drives the eupago hosted card form (Shift4) with the official test card
``4018810000150015`` and OTP ``0101`` — amounts above 500 EUR trigger the
3D-Secure challenge, so we test the full path:

    SDK create_payment  ->  redirectUrl  ->  Playwright fills card + OTP
       ->  eupago redirects to successUrl
       ->  webhook arrives at the AWS receiver
       ->  SDK parse_webhook validates the captured bytes (status = Paid)

Requires:
- ``EUPAGO_API_KEY``, ``EUPAGO_WEBHOOK_TABLE``, ``EUPAGO_WEBHOOK_SECRET``
- the ``e2e`` extra installed (``pip install eupago[e2e]`` + ``playwright install chromium``)
- AWS credentials for the DynamoDB capture table

Skipped automatically otherwise.
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

_API_KEY = os.environ.get("EUPAGO_API_KEY")
_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET")
_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_RETURN_BASE = os.environ.get("EUPAGO_CC_RETURN_BASE", "https://breathpilates.pt")
_HEADFUL = os.environ.get("EUPAGO_PW_HEADFUL", "0") == "1"

pytestmark = pytest.mark.skipif(
    not (_API_KEY and _SECRET and _TABLE),
    reason="set EUPAGO_API_KEY/EUPAGO_WEBHOOK_TABLE/EUPAGO_WEBHOOK_SECRET to run 3DS E2E",
)

# Official eupago sandbox test card
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

    # The submit button is the only <button> on the page; its label is the
    # localised "Pay X EUR" string. Wait until it stops being disabled.
    btn = page.get_by_role("button").first
    btn.wait_for(state="visible")
    page.wait_for_function(
        "() => Array.from(document.querySelectorAll('button')).some(b => !b.disabled)",
        timeout=10_000,
    )
    btn.click()


def _fill_otp(page: Any, otp: str) -> None:
    """The sandbox 3DS simulator (Credorax ACS) renders ``input[name="otp"]``
    and a ``Pay`` button at ``x3d-sim.credorax.net/acs/challenge``. We type
    keystrokes (not ``fill``) so the simulator's keyup handler enables Pay."""
    page.wait_for_url("**x3d-sim.credorax.net/acs/challenge**", timeout=30_000)
    page.wait_for_selector('input[name="otp"]', timeout=15_000)
    field = page.locator('input[name="otp"]')
    field.click()
    field.press_sequentially(otp, delay=50)
    pay = page.get_by_role("button", name="Pay")
    pay.wait_for(state="visible")
    page.wait_for_function(
        "() => {\n"
        "  const b = Array.from(document.querySelectorAll('button'))\n"
        "    .find(x => x.textContent.trim() === 'Pay');\n"
        "  return b && !b.disabled;\n"
        "}",
        timeout=10_000,
    )
    pay.click()


def _wait_for_webhook(table: Any, order_id: str, timeout: int = 90) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


@pytest.mark.integration
def test_credit_card_3ds_paid_flow(client: Any, browser: Any, table: Any) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-CC3DS-{uuid.uuid4().hex[:10]}"
    payment = client.credit_card.create_payment(
        order_id=order_id,
        amount=Decimal("600.00"),  # > 500 EUR -> OTP challenge
        success_url=f"{_RETURN_BASE}/ok",
        error_url=f"{_RETURN_BASE}/err",
        back_url=f"{_RETURN_BASE}/back",
    )
    assert payment.payment_url is not None

    page = browser.new_page()
    try:
        page.goto(payment.payment_url, wait_until="networkidle", timeout=30_000)
        _fill_card_form(page)
        _fill_otp(page, TEST_OTP_SUCCESS)
        # Wait for the post-OTP navigation to leave the ACS challenge page —
        # eupago handles the final merchant redirect server-side, but the
        # webhook fires regardless, so we don't pin a specific success URL.
        page.wait_for_url(
            lambda url: "x3d-sim.credorax.net/acs/challenge" not in url,
            timeout=45_000,
        )
    finally:
        page.close()

    item = _wait_for_webhook(table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
    assert event.method == "credit_card"
