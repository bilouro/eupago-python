# Credit Card

## What it is

Hosted credit/debit card payment with 3D-Secure / OTP. The customer is
redirected to eupago's hosted form to enter the card details and (when the
card or the amount requires it) complete the challenge. The final outcome
arrives via webhook.

The same service covers three flows:

- **`create_payment`** — single one-shot charge.
- **`authorize` + `capture`** — reserve now, charge later.
- **`create_subscription` + `charge_subscription`** — register a card once,
  then charge it from the server on demand.

The maximum amount per transaction is **3,999 EUR**.

## Flow

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Customer
    App->>eupago: create_payment(amount, success_url, error_url, back_url)
    eupago-->>App: redirectUrl + transactionID (status PENDING)
    App->>Customer: Redirect to redirectUrl
    Customer->>eupago: Enters card details + (optional) 3DS OTP
    eupago->>App: Webhook (PAID / DECLINED)
```

## Example — one-shot

```python
from decimal import Decimal
from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="...", sandbox=True)

payment = client.credit_card.create_payment(
    order_id="ORD-CC-001",
    amount=Decimal("249.90"),
    success_url="https://shop.example.com/ok",
    error_url="https://shop.example.com/fail",
    back_url="https://shop.example.com/cart",
    customer=Customer(email="customer@example.com"),
)

# Redirect the customer to payment.payment_url and wait for the webhook
```

**Sandbox test card:** `4018810000150015` (Visa) — OTP `0101` succeeds,
`3333` fails. Amounts above 500 EUR trigger the OTP prompt.

## Example — authorize + capture

```python
auth = client.credit_card.authorize(
    order_id="ORD-CC-AUTH-001",
    amount=Decimal("100.00"),
    success_url="...", error_url="...", back_url="...",
)

# Later, when the goods ship:
captured = client.credit_card.capture(transaction_id=auth.transaction_id)
```

## Example — subscription

```python
sub = client.credit_card.create_subscription(
    order_id="SUB-2026-001",
    amount=Decimal("0.00"),  # 0 = card registration only
    success_url="...", error_url="...", back_url="...",
)

# Once the webhook delivers a recurrent_id:
client.credit_card.charge_subscription(
    recurrent_id=12345,
    order_id="SUB-2026-001-M01",
    amount=Decimal("19.90"),
)
```

## Refund

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    value=Decimal("249.90"),
)
```

See [Refunds](refund.md) for OAuth setup.

## Notes

- All three return URLs (`success_url`, `error_url`, `back_url`) are
  required by the API for `create_payment`, `authorize`, and
  `create_subscription`.
- Subscriptions store the card token on eupago's side; subsequent charges
  do not require customer interaction.
- See the runnable
  [`07_credit_card_payment.py`](https://github.com/bilouro/eupago-python/blob/main/examples/07_credit_card_payment.py)
  and
  [`08_credit_card_subscription.py`](https://github.com/bilouro/eupago-python/blob/main/examples/08_credit_card_subscription.py)
  for the full lifecycle.
