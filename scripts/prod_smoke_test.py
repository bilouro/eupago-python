"""One-shot production smoke test for eupago.

Runs a single real payment in production against the configured channel
and asserts the webhook lands at the AWS receiver. Intended to be run
manually (NOT in CI) once per payment method, to validate the live
production setup end-to-end.

Usage::

    set -a; source .env; set +a   # plus AWS_PROFILE=breath-admin
    python scripts/prod_smoke_test.py mbway       # €1.00 MB WAY push
    python scripts/prod_smoke_test.py multibanco  # €1.00 entity/reference

Required env vars:
- EUPAGO_PROD_API_KEY            channel API key (production)
- EUPAGO_PROD_WEBHOOK_SECRET     channel Chave Criptográfica
- EUPAGO_WEBHOOK_TABLE           DynamoDB capture table (shared with sandbox infra)
- EUPAGO_PROD_MBWAY_PHONE        9-digit PT phone for MB WAY (only for `mbway`)
- AWS credentials reaching the receiver table (breath-admin profile)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from decimal import Decimal
from typing import Any

import boto3

from eupago import EupagoClient, PaymentStatus

_AMOUNT = Decimal("1.00")
_POLL_INTERVAL_SECS = 5


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"missing env var: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def _client() -> EupagoClient:
    return EupagoClient(
        api_key=_env("EUPAGO_PROD_API_KEY"),
        webhook_secret=_env("EUPAGO_PROD_WEBHOOK_SECRET"),
        sandbox=False,
    )


def _table() -> Any:
    return boto3.resource("dynamodb").Table(_env("EUPAGO_WEBHOOK_TABLE"))


def _wait_for_webhook(table: Any, order_id: str, timeout: int) -> dict[str, Any] | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            return item  # type: ignore[no-any-return]
        remaining = int(deadline - time.time())
        print(f"  …no webhook yet, {remaining}s remaining", flush=True)
        time.sleep(_POLL_INTERVAL_SECS)
    return None


def _verify_webhook(client: EupagoClient, item: dict[str, Any]) -> None:
    event = client.webhooks.parse(body=item["raw_body"], headers=json.loads(item["headers"]))
    print(
        f"  webhook parsed: order_id={event.order_id} method={event.method} "
        f"status={event.status} amount={event.amount}"
    )
    assert event.status == PaymentStatus.PAID, f"unexpected status: {event.status}"


def run_mbway(timeout_secs: int = 360) -> int:
    phone = _env("EUPAGO_PROD_MBWAY_PHONE")
    client = _client()
    table = _table()
    order_id = f"PROD-MW-{uuid.uuid4().hex[:10]}"

    print(f"→ MB WAY create_payment €{_AMOUNT} for phone {phone} (order_id={order_id})")
    result = client.mbway.create_payment(
        order_id=order_id,
        amount=_AMOUNT,
        phone_number=phone,
    )
    print(f"  ok → transaction_id={result.transaction_id} status={result.status}")
    print("\n📱 Approve the MB WAY push on your phone now (you have 5 min).\n")

    item = _wait_for_webhook(table, order_id, timeout_secs)
    if item is None:
        print(
            f"✗ no webhook received within {timeout_secs}s — was the push approved?",
            file=sys.stderr,
        )
        return 1

    _verify_webhook(client, item)
    print(f"✅ MB WAY production smoke test PASSED — €{_AMOUNT} approved + webhook verified")
    return 0


def run_multibanco(timeout_secs: int = 1800) -> int:
    client = _client()
    table = _table()
    order_id = f"PROD-MB-{uuid.uuid4().hex[:10]}"

    print(f"→ Multibanco create_reference €{_AMOUNT} (order_id={order_id})")
    ref = client.multibanco.create_reference(order_id=order_id, amount=_AMOUNT)
    print(f"  ok → entity={ref.entity} reference={ref.reference}")
    print(
        f"\n🏦 Pay via homebanking:\n"
        f"     Entidade:    {ref.entity}\n"
        f"     Referência:  {ref.reference}\n"
        f"     Montante:    {_AMOUNT} EUR\n"
    )

    item = _wait_for_webhook(table, order_id, timeout_secs)
    if item is None:
        print(
            f"✗ no webhook received within {timeout_secs}s — keep the order_id "
            f"({order_id}) and re-check the DDB later if you pay outside this window.",
            file=sys.stderr,
        )
        return 1

    _verify_webhook(client, item)
    print(f"✅ Multibanco production smoke test PASSED — €{_AMOUNT} paid + webhook verified")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=["mbway", "multibanco"])
    args = parser.parse_args()
    if args.method == "mbway":
        return run_mbway()
    return run_multibanco()


if __name__ == "__main__":
    raise SystemExit(main())
