# Refunds

## What they are

Reverse a previously paid transaction — total or partial. Works for any
payment method (MB WAY, Multibanco, Credit Card, Apple/Google Pay,
Pay By Link, …).

Refunds use eupago's **management API**, which is a separate auth surface
from the regular payment endpoints.

## ⚠️ No webhook on refunds

Unlike payments, **eupago does not emit a webhook for refunds**. Treat the
synchronous response as the source of truth:

```python
if result.status == PaymentStatus.REFUNDED:
    ...
```

If you need a second source of truth, poll the management transactions
endpoint after the refund.

## Getting the OAuth credentials

The refund endpoint requires `client_id` + `client_secret`, **not** the
regular API Key:

- These are **not self-service in the backoffice**.
- They are issued by **eupago support on request** (open a ticket via
  [customer.support.eupago.com](https://customer.support.eupago.com/) or
  email `suporte@eupago.pt`).
- The same pair gates every `/api/management/...` endpoint.

Once you have them, configure the client once:

```python
client = EupagoClient(
    api_key="...",
    client_id="...",
    client_secret="...",
    sandbox=True,
)
```

The SDK manages the token lifecycle: it requests `/api/auth/token` with
`grant_type=client_credentials`, caches the Bearer, and refreshes on
expiry — there is nothing for you to do.

## Example

```python
from decimal import Decimal
from eupago import EupagoClient, PaymentStatus

client = EupagoClient(
    api_key="...",
    client_id="...",
    client_secret="...",
    sandbox=True,
)

# Full refund
result = client.refunds.refund(
    transaction_id="113068862",
    value=Decimal("64.00"),
    reason="Customer cancelled",
)

assert result.status == PaymentStatus.REFUNDED
```

## Partial refund

```python
partial = client.refunds.refund(
    transaction_id="113068862",
    value=Decimal("20.00"),  # less than the original amount
    reason="Partial return — 1 item of 3",
)
```

## Parameters

| Parameter        | Type      | Required | Description |
|------------------|-----------|----------|-------------|
| `transaction_id` | `str`     | Yes      | ID of the original transaction (from the payment response or the webhook) |
| `value`          | `Decimal` | Yes      | Amount to refund (≤ original amount) |
| `currency`       | `str`     | No       | ISO 4217. Default `"EUR"` |
| `reason`         | `str`     | No       | Free-text reason, stored in the transaction history |

## Async

```python
async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
    result = await c.refunds.refund_async(
        transaction_id="113068862",
        value=Decimal("64.00"),
    )
```
