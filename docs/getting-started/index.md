# Installation & Quickstart

## Installation

```bash
pip install eupago
```

Requires Python 3.9+. The only dependencies are [httpx](https://www.python-httpx.org/) and [Pydantic v2](https://docs.pydantic.dev/).

## First payment

### 1. Get your API Key

In the eupago backoffice, go to **Channels** > **Channel Listing** and copy the API Key.

### 2. Create the client

```python
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,  # False for production
)
```

### 3. Create an MB WAY payment

```python
from decimal import Decimal

payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="351#912345678",
)

print(payment.transaction_id)  # Transaction ID
print(payment.status)          # PaymentStatus.PENDING
```

The customer receives a push notification and has 5 minutes to approve.

### 4. Receive the webhook

When the customer pays, eupago sends a webhook to your server:

```python
from eupago.webhooks import parse_webhook

event = parse_webhook(
    body=request.body,
    headers=request.headers,
    webhook_secret="your-secret",
)

if event.status == PaymentStatus.PAID:
    # Mark order as paid
    ...
```

## Async

Every method has an async variant — same client, `_async` suffix:

```python
async with EupagoClient(api_key="...", sandbox=True) as client:
    payment = await client.mbway.create_payment_async(
        order_id="ORD-001",
        amount=Decimal("49.90"),
        phone_number="351#912345678",
    )
```

## Next steps

- [Configuration](configuration.md) — sandbox, timeout, OAuth, audit hook
- [Which method to choose?](../payments/index.md) — decision guide
- [Webhooks](../webhooks/index.md) — receive notifications
