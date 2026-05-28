# Webhooks

## How they work

When a payment is confirmed (e.g. the customer approves on MB WAY, or pays at an ATM), eupago sends an HTTP notification to your server — the **webhook**.

Your server must:

1. Receive the request
2. Verify authenticity (HMAC signature on v2.0)
3. Update the order in your database
4. Respond with **HTTP 200**

```
Customer pays ──► eupago processes ──► Webhook to your server
                                            │
                                            ▼
                                      Update order
```

!!! warning "Always return HTTP 200"
    If your server does not return 200, eupago will retry the webhook:

    - Every **2 minutes**, up to **3 attempts**
    - Then, **every hour** for **24 hours**

    After that period, the webhook is discarded.

---

## Webhook versions

eupago supports two webhook versions. We recommend v2.0.

### v1.0 — Legacy (GET)

The webhook is sent as a **GET** request with query parameters:

| Parameter | Description | Example |
|---|---|---|
| `valor` | Amount paid | `49.90` |
| `identificador` | Order ID (yours) | `ORD-2026-001` |
| `transacao` | eupago transaction ID | `78901` |
| `referencia` | Payment reference | `999888777` |
| `entidade` | Multibanco entity | `12345` |
| `mp` | Payment method | `MW:PT` |
| `chave_api` | API key (for validation) | `xxxx-xxxx` |
| `data` | Payment date | `2026-05-26` |

### v2.0 — Recommended (POST + HMAC)

The webhook is sent as a **POST** request with a JSON body and HMAC-SHA256 signature in the `X-Signature` header.

```json
{
  "transactions": {
    "entity": 12345,
    "reference": 999888777,
    "identifier": "ORD-2026-001",
    "method": "Mbway",
    "amount": {"value": 49.90, "currency": "EUR"},
    "fees": {"value": 0.35, "currency": "EUR"},
    "date": "2026-05-26T14:30:00Z",
    "trid": 78901,
    "status": "Paid"
  },
  "channel": {"name": "main-channel"}
}
```

**Headers:**

| Header | Description |
|---|---|
| `X-Signature` | HMAC-SHA256 of the body using your webhook secret |
| `X-Initialization-Vector` | IV for AES decryption (optional) |
| `Content-Type` | `application/json` |

!!! tip "Always use v2.0"
    v2.0 includes HMAC signature to prevent forgery, and optionally AES-256-CBC encryption to protect sensitive data in transit.

---

## Using the SDK

The SDK abstracts both versions with a single function: `parse_webhook()`.

### Webhook v2.0 (POST)

```python
from eupago.webhooks import parse_webhook
from eupago.models import PaymentStatus

event = parse_webhook(
    body=request.body,
    headers=dict(request.headers),
    webhook_secret="your-secret",  # HMAC verification is automatic
)

if event.status == PaymentStatus.PAID:
    print(f"Order {event.order_id} paid: {event.amount} {event.currency}")
```

### Webhook v1.0 (GET)

```python
from eupago.webhooks import parse_webhook

event = parse_webhook(query_params=dict(request.query_params))

print(f"Order {event.order_id} paid: {event.amount} {event.currency}")
```

### The `WebhookEvent` object

Both versions return a `WebhookEvent` with normalized fields:

| Field | Type | Description |
|---|---|---|
| `order_id` | `str \| None` | Your order ID |
| `transaction_id` | `str \| None` | eupago transaction ID |
| `reference` | `str \| None` | Payment reference |
| `entity` | `str \| None` | Multibanco entity |
| `amount` | `Decimal \| None` | Amount paid |
| `currency` | `str` | Currency (default `"EUR"`) |
| `status` | `PaymentStatus` | Normalized status |
| `method` | `str \| None` | Normalized payment method |
| `paid_at` | `str \| None` | Payment date/time |
| `channel` | `str \| None` | eupago channel |
| `fee` | `Decimal \| None` | eupago fee |

---

## Configuring in the backoffice

1. Access the [eupago backoffice](https://sandbox.eupago.pt) (sandbox) or [production](https://clientes.eupago.pt)
2. Go to **Canais** > **Listagem de Canais**
3. Select the desired channel
4. In **Callback URL**, enter your endpoint URL (e.g. `https://myshop.com/eupago/callback`)
5. Choose the webhook version (we recommend v2.0)
6. If v2.0, copy the **Webhook Secret** to your application

!!! warning "HTTPS required"
    eupago only sends webhooks to HTTPS URLs in production. For development, use tools like [ngrok](https://ngrok.com/) to expose your local server.

---

## Next steps

- [Signature verification](signature.md) — HMAC-SHA256 and AES encryption
- [Recipes](../recipes/index.md) — complete examples with FastAPI, Django, Flask
