"""End-to-end subscription management against the eupago sandbox.

Exercises the 4 Management API methods exposed on the CreditCardService:

- ``list_subscriptions()``
- ``get_subscription(subscription_id)``
- ``edit_subscription(subscription_id, collection_day=…, auto_process=…)``
- ``revoke_subscription(subscription_id)`` — skipped when no active sub

Uses the backoffice login Bearer (via ``management_bearer``) as the auth
path, mirroring ``test_refund_live.py``. We mutate the channel state, so
we always restore it at the end.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from .sandbox_backoffice import BackofficeSession

_API_KEY = os.environ.get("EUPAGO_API_KEY")
_BO_EMAIL = os.environ.get("EUPAGO_BACKOFFICE_EMAIL")
_BO_PASS = os.environ.get("EUPAGO_BACKOFFICE_PASSWORD")

pytestmark = pytest.mark.skipif(
    not (_API_KEY and _BO_EMAIL and _BO_PASS),
    reason=(
        "set EUPAGO_API_KEY/EUPAGO_BACKOFFICE_EMAIL/EUPAGO_BACKOFFICE_PASSWORD "
        "to run subscription management live tests"
    ),
)


@pytest.fixture(scope="module")
def backoffice() -> Iterator[BackofficeSession]:
    with BackofficeSession(_BO_EMAIL or "", _BO_PASS or "") as s:
        yield s


@pytest.fixture
def client(backoffice: BackofficeSession) -> Any:
    from eupago import EupagoClient

    return EupagoClient(
        api_key=_API_KEY or "",
        sandbox=True,
        management_bearer=backoffice._bearer,
    )


# Demo channel anchor — bumped as we add more subs. The list endpoint does
# NOT include the integer ``subscriptionId`` (a real eupago UX gap), so the
# integer needs to come from the backoffice URL. For this test channel the
# ids are sequential 4756..4760+, so we scan around the known head.
_KNOWN_DEMO_ID_RANGE = range(4760, 4750, -1)


def _find_subscription_id(client: Any) -> int | None:
    rows = client.credit_card.list_subscriptions()
    if not rows:
        return None
    tokens = {row["eupagoToken"] for row in rows}
    for sid in _KNOWN_DEMO_ID_RANGE:
        try:
            d = client.credit_card.get_subscription(sid)
        except Exception:  # noqa: S112 — IDs that don't exist 404, expected
            continue
        if d.get("eupagoToken") in tokens:
            return sid
    return None


@pytest.mark.integration
def test_list_get_edit_subscription_live(client: Any) -> None:
    rows = client.credit_card.list_subscriptions()
    if not rows:
        pytest.skip("no subscriptions on the demo channel — create one first")
    # Every row has these fields per the verified list response shape.
    assert "eupagoToken" in rows[0]
    assert "reference" in rows[0]
    assert "status" in rows[0]

    sid = _find_subscription_id(client)
    assert sid is not None, "no integer subscription_id resolved from the list"

    detail = client.credit_card.get_subscription(sid)
    assert detail["subscriptionId"] == str(sid)
    original_day = int(detail["payment"].get("collectionDay") or 1)
    original_auto = detail["payment"].get("autoProcess") == "1"

    # Mutate and restore — we don't want to leave the channel in a weird state.
    probe_day = (original_day % 28) + 1
    try:
        edit_result = client.credit_card.edit_subscription(
            sid, collection_day=probe_day, auto_process=not original_auto
        )
        assert edit_result.get("transactionStatus") == "Success"

        refetched = client.credit_card.get_subscription(sid)
        assert int(refetched["payment"]["collectionDay"]) == probe_day
        # autoProcess flips correctly: 1 -> absent or "0"; 0 -> "1"
        new_auto = refetched["payment"].get("autoProcess") == "1"
        assert new_auto is (not original_auto)
    finally:
        client.credit_card.edit_subscription(
            sid, collection_day=original_day, auto_process=original_auto
        )


@pytest.mark.integration
def test_revoke_subscription_only_works_on_active(client: Any) -> None:
    """Revoke on a Pendente subscription must raise SUBSCRIPTION_NOT_FOUND —
    confirms the SDK propagates eupago's error correctly. (When the channel
    has an active subscription this can be promoted to a full happy-path
    test.)
    """
    from eupago.exceptions import ApiError

    sid = _find_subscription_id(client)
    if sid is None:
        pytest.skip("no subscriptions on the channel")

    detail = client.credit_card.get_subscription(sid)
    if detail.get("status") != "Pendente":
        # If a future test channel has an active sub, this test should be
        # rewritten to actually revoke (and recreate after).
        pytest.skip(
            f"subscription {sid} is in status={detail.get('status')} (not Pendente); "
            "this test only validates the error path"
        )

    with pytest.raises(ApiError) as exc_info:
        client.credit_card.revoke_subscription(sid)
    assert exc_info.value.error_code == "SUBSCRIPTION_NOT_FOUND"


@pytest.mark.integration
def test_create_subscription_then_appears_in_list(client: Any) -> None:
    """After SDK create_subscription, the new sub shows up in list_subscriptions.
    The Pendente status reflects that the card-registration form was never
    completed (a Playwright drive would convert it to active — but the form
    redirects to errorUrl on the demo channel)."""
    from decimal import Decimal

    order_id = f"ITEST-SUBMGMT-{uuid.uuid4().hex[:10]}"
    sub = client.credit_card.create_subscription(
        order_id=order_id,
        amount=Decimal("9.99"),
        success_url="https://breathpilates.pt/ok",
        error_url="https://breathpilates.pt/err",
        back_url="https://breathpilates.pt/back",
    )
    assert sub.transaction_id is not None

    rows = client.credit_card.list_subscriptions()
    matching = [r for r in rows if r["identifier"] == order_id]
    assert matching, f"{order_id} did not show up in list_subscriptions"
    assert matching[0]["eupagoToken"] == sub.transaction_id
    assert matching[0]["status"] == "Pendente"
