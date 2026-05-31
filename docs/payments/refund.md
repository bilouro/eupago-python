# Refunds

## What they are

Reverse a previously paid transaction — total or partial. Works for any
payment method (MB WAY, Multibanco, Credit Card, Apple/Google Pay,
Pay By Link, …).

Refunds use eupago's **management API**, which is a separate auth surface
from the regular payment endpoints.

## Refund webhooks (eupago docs say "no", in practice "yes")

The eupago documentation claims no webhook fires on refunds. **In production
it does** — confirmed live on 2026-05-31:

```json
{
  "transaction": {
    "method": "RB:PT",                    // reembolso
    "status": "REFUNDED",                 // uppercase here, "Reembolsado" in the sync response
    "trid": "113194712",                  // the refund's own transaction_id
    "originalTrid": "113193247",          // the trid of the payment being refunded ← reconciliation
    "identifier": "PROD-MW-74685211ac",
    "amount": {"value": 1, "currency": "EUR"}
  }
}
```

The SDK parses these correctly:

```python
event = client.webhooks.parse(body=request.body, headers=request.headers)
if event.method == "refund" and event.status == PaymentStatus.REFUNDED:
    # link back to the original payment without keeping your own mapping
    original_payment_id = event.original_transaction_id
```

The synchronous response (200/201 + ``refundId``) is still authoritative.
The webhook is useful for **reconciliation** — particularly when the refund
comes from outside your SDK call path (e.g. an admin doing it in the
backoffice).

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

# Full refund for an MB WAY or Credit Card transaction (no IBAN needed)
result = client.refunds.refund(
    transaction_id="29748010",
    amount=Decimal("3.45"),
    reason="Customer cancelled",
)

assert result.status == PaymentStatus.REFUNDED
refund_id = result.raw_response["refundId"]  # eupago refund id (for audit)
```

## Multibanco refunds need IBAN **and** BIC

Multibanco settles bank-to-bank, so the refund needs to know where to send
the money back. **Both `iban` and `bic` are required** despite the docs
suggesting `bic` is optional — without it eupago returns
`BIC_INVALID` (live-verified in production, 2026-05-31):

```python
client.refunds.refund(
    transaction_id="113068862",
    amount=Decimal("40.00"),
    iban="PT50000201231234567890154",   # customer IBAN
    bic="BCOMPTPL",                      # required (lookup from the IBAN's bank code)
)
```

Settlement is **asynchronous**: the synchronous response carries
`status: "Pendente"` (instead of the immediate `"Reembolsado"` you get on
MB WAY/Card refunds). The settlement webhook arrives later when the bank
transfer actually clears — could be minutes, could be hours. Use
`WebhookEvent.original_transaction_id` to reconcile.

MB WAY and Credit Card refunds settle wallet-/card-to-card and don't need
IBAN/BIC.

## Partial refund

```python
partial = client.refunds.refund(
    transaction_id="29748010",
    amount=Decimal("1.00"),  # less than the original amount
    reason="Partial return — 1 item of 3",
)
```

## Parameters

| Parameter        | Type      | Required | Description |
|------------------|-----------|----------|-------------|
| `transaction_id` | `str`     | Yes      | ID of the original transaction (from the payment response or the webhook) |
| `amount`         | `Decimal` | Yes      | Amount to refund (≤ original amount) |
| `reason`         | `str`     | No       | Free-text reason, stored in the transaction history |
| `iban`           | `str`     | Yes for Multibanco | Customer bank account for bank-to-bank refunds |
| `bic`            | `str`     | No       | Routing code; rarely required |

## Async

```python
async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
    result = await c.refunds.refund_async(
        transaction_id="29748010",
        amount=Decimal("3.45"),
    )
```

## Test escape hatch — injecting a backoffice Bearer

The eupago backoffice login (`/api/auth/login`) returns a Bearer token
that works on the same `/api/management/*` endpoints, with the body
shapes the management API expects. While you wait for the OAuth
credentials from support, you can drive refunds from a test/script with
that bearer:

```python
client = EupagoClient(
    api_key="...",
    management_bearer="<bearer from /api/auth/login>",
    sandbox=True,
)
client.refunds.refund(transaction_id="...", amount=Decimal("..."))
```

This bypasses OAuth entirely. Production callers should still use
`client_id`/`client_secret`.
