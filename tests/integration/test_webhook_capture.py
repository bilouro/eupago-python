"""Live webhook capture test (guided integration test).

Requires the AWS receiver from ``tests/integration/infra`` deployed and the
eupago sandbox channel pointed at its ``webhook_url``. Run deliberately:

    export EUPAGO_API_KEY=...
    export EUPAGO_WEBHOOK_TABLE=...        # table_name output from terraform
    export EUPAGO_WEBHOOK_SECRET=...       # only if the channel encrypts webhooks
    pytest -m integration tests/integration/test_webhook_capture.py -s

It creates a Multibanco reference, waits for you to mark it "Paga" in the
backoffice, then validates that the captured webhook parses via the SDK.
Skipped automatically unless boto3 and the env vars are present, so the normal
suite stays green.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from decimal import Decimal

import pytest

boto3 = pytest.importorskip("boto3")

_TABLE = os.environ.get("EUPAGO_WEBHOOK_TABLE")
_API_KEY = os.environ.get("EUPAGO_API_KEY")

pytestmark = pytest.mark.skipif(
    not (_TABLE and _API_KEY),
    reason="set EUPAGO_WEBHOOK_TABLE and EUPAGO_API_KEY to run the live capture test",
)


@pytest.mark.integration
def test_multibanco_webhook_capture() -> None:
    from eupago import EupagoClient
    from eupago.webhooks import parse_webhook

    client = EupagoClient(api_key=_API_KEY, sandbox=True)
    order_id = f"ITEST-{uuid.uuid4().hex[:10]}"
    ref = client.multibanco.create_reference(order_id=order_id, amount=Decimal("1.00"))

    print("\n>>> Mark this reference as PAID in the eupago sandbox backoffice:")
    print(f"    Operações > Consultar > Transações > {ref.entity} / {ref.reference}")
    print(f"    > Ações > 'Marcar como Paga'   (order_id={order_id})\n")

    table = boto3.resource("dynamodb").Table(_TABLE)
    timeout = int(os.environ.get("EUPAGO_WEBHOOK_TIMEOUT", "300"))
    deadline = time.time() + timeout
    item = None
    while time.time() < deadline:
        item = table.get_item(Key={"order_id": order_id}).get("Item")
        if item:
            break
        time.sleep(5)

    assert item is not None, f"no webhook captured for {order_id} within {timeout}s"

    headers = json.loads(item["headers"])
    event = parse_webhook(
        body=item["raw_body"],
        headers=headers,
        webhook_secret=os.environ.get("EUPAGO_WEBHOOK_SECRET"),
    )
    assert event.reference == str(ref.reference)
    print(f"captured + parsed OK: status={event.status} reference={event.reference}")
