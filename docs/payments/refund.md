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
regular API Key. As of 2026-06, these are **self-service in the
backoffice** (eupago changed their process):

1. Log into `clientes.eupago.pt`
2. Top-right user menu → **A Minha Conta** → tab **Credenciais**
3. Click **"+ Criar Credenciais"**, name them, **Gerar**
4. **Save the Client Secret immediately** — it's only shown once. The
   Client ID can be re-fetched any time.

Credentials expire in **1 year** and can be revoked at any time from the
same panel. They are **per user**, not per channel — the same pair gates
every `/api/management/...` endpoint on every channel you own.

Live-verified in production on 2026-06-07.

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
suggesting `bic` is optional — without it eupago returns `BIC_INVALID`
(definitively probed in production on 2026-05-31: `bic` missing, `""` and
`null` all rejected; only a non-empty string is accepted):

```python
from eupago.utils import bic_for_pt_iban

customer_iban = "PT50000201231234567890154"
client.refunds.refund(
    transaction_id="113068862",
    amount=Decimal("40.00"),
    iban=customer_iban,
    bic=bic_for_pt_iban(customer_iban),  # SDK helper for the top PT banks
)
```

`bic_for_pt_iban` covers the major retail banks in Portugal (~99% of
consumer accounts). It returns `None` for niche banks — in that case fall
back to asking the customer.

## Settlement is asynchronous (and you can poll for it)

Multibanco refunds carry `status: "Pendente"` in the synchronous response
(MB WAY / Card refunds get the immediate `"Reembolsado"`). The settlement
webhook fires later when the bank transfer clears — minutes to hours. Use
`WebhookEvent.original_transaction_id` to reconcile.

If you'd rather poll than wait for the webhook:

```python
state = client.refunds.get(refund_id)
# {"identifier": "ORD-...", "reference": "...", "status": "pendente"}
# changes to "Reembolsado" once settled
```

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
