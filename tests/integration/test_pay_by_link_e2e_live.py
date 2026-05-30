"""End-to-end Pay By Link against the eupago sandbox.

Flow::

    SDK pay_by_link.create_payment  ->  redirectUrl ".../paybylink/form/<id>"
       ->  Playwright opens the link  ->  picks a method (MB WAY)
       ->  fills the method-specific form  ->  backoffice marks paid
       ->  webhook arrives at the AWS receiver
       ->  SDK parse_webhook validates the captured bytes (status = Paid)

**Channel capability:** Pay By Link only offers methods that are individually
enabled on the eupago channel ("Métodos de pagamento" in the backoffice).
If the channel has none enabled the customer-facing page renders
"Não há métodos de pagamento disponíveis" and the E2E flow cannot be
exercised — the test is then skipped with a clear reason instead of
failing the suite. The SDK call itself (URL generation, response
parsing) is already covered live by ``test_pay_by_link_live.py``.
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

from .sandbox_backoffice import BackofficeSession  # noqa: E402

_API_KEY = os.environ.get("EUPAGO_API_KEY")
_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET")
_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_BO_EMAIL = os.environ.get("EUPAGO_BACKOFFICE_EMAIL")
_BO_PASS = os.environ.get("EUPAGO_BACKOFFICE_PASSWORD")
_HEADFUL = os.environ.get("EUPAGO_PW_HEADFUL", "0") == "1"

pytestmark = pytest.mark.skipif(
    not (_API_KEY and _SECRET and _TABLE and _BO_EMAIL and _BO_PASS),
    reason=(
        "set EUPAGO_API_KEY/EUPAGO_WEBHOOK_TABLE/EUPAGO_WEBHOOK_SECRET/"
        "EUPAGO_BACKOFFICE_* to run Pay By Link E2E"
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


@pytest.fixture
def browser() -> Iterator[Any]:
    with pw.sync_playwright() as p:
        b = p.chromium.launch(headless=not _HEADFUL)
        yield b
        b.close()


def _wait_for_webhook(table: Any, order_id: str, timeout: int = 90) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        time.sleep(3)
    pytest.fail(f"no webhook captured for {order_id} within {timeout}s")


@pytest.mark.integration
def test_pay_by_link_customer_completes_via_mbway(
    client: Any, browser: Any, backoffice: BackofficeSession, table: Any
) -> None:
    from eupago.models.payment import PaymentStatus

    order_id = f"ITEST-PBLE2E-{uuid.uuid4().hex[:10]}"
    link = client.pay_by_link.create_payment(order_id=order_id, amount=Decimal("1.23"))
    assert link.payment_url is not None
    assert "paybylink/form/" in link.payment_url

    page = browser.new_page()
    try:
        page.goto(link.payment_url, wait_until="networkidle", timeout=30_000)
        body_text = page.locator("body").inner_text()
        if "Não há métodos de pagamento" in body_text or "No payment methods" in body_text:
            pytest.skip(
                "Pay By Link page renders 'no payment methods available' — the "
                "eupago channel has no methods enabled in the Pay By Link "
                "section of the backoffice. The SDK URL generation is already "
                "covered live by test_pay_by_link_live.py; this E2E requires a "
                "channel where at least one method (e.g. MB WAY) is enabled."
            )
        # If the page does offer methods, pick MB WAY by clicking its option.
        mbway_option = page.get_by_text("MB WAY", exact=False).first
        mbway_option.click()
        page.wait_for_load_state("networkidle", timeout=15_000)
        # MB WAY sub-form usually shows a phone input + submit.
        phone_input = page.locator(
            'input[type="tel"], input[name*="phone"], input[name*="telefone"]'
        ).first
        phone_input.fill("912345678")
        page.get_by_role("button").first.click()
    finally:
        page.close()

    backoffice.mark_paid_by_identifier(order_id)

    item = _wait_for_webhook(table, order_id)
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    assert event.order_id == order_id
    assert event.status == PaymentStatus.PAID
