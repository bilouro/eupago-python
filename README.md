# eupago

[![PyPI version](https://img.shields.io/pypi/v/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![CI](https://img.shields.io/github/actions/workflow/status/bilouro/eupago-python/test.yml?branch=main&style=flat-square&label=CI)](https://github.com/bilouro/eupago-python/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-mypy--strict-blue.svg?style=flat-square)](https://mypy.readthedocs.io/)
[![Docs](https://img.shields.io/badge/docs-eupago.bilouro.com-blue.svg?style=flat-square)](https://eupago.bilouro.com/)

**eupago for Python** — accept MB WAY, Multibanco, credit-card and Pay By Link
payments in Portugal with a modern, fully-typed Python SDK. The first
community SDK for [eupago](https://www.eupago.com), Portugal's leading
payment gateway. Production-validated: every payment method here has been
exercised against a live eupago channel with real money.

Built like the Stripe SDK should look in Python: sync + async on the same
client, `Decimal` for money (never float), HMAC-verified webhooks (cleartext
and AES-256-CBC encrypted), automatic retries on GETs (POSTs never retry —
no idempotency = duplicate payments), and a unified vocabulary that hides
eupago's two API generations behind one clean interface.

📖 Documentation: <https://eupago.bilouro.com/> · English<br>
📖 Documentation: <https://eupago.bilouro.com/pt> · Português

[Examples](examples/) · [API Reference](https://eupago.bilouro.com/api/)

> **Community SDK** — not affiliated with or endorsed by eupago.
> For official integrations, visit [eupago.com](https://www.eupago.com/integrations/api-payment-gateway).

## Status

Per-operation coverage. **Unit** = `respx`-mocked unit test asserting the wire body.
**Sandbox** = integration test against the eupago sandbox.
**Prod** = real production transaction exercised against a live eupago channel
on 2026-05-31 (real money moved + verified back via webhook).

| Operation | Unit | Sandbox | Prod |
|---|:-:|:-:|:-:|
| `mbway.create_payment` (sync + async) | ✅ | ✅ | ✅ |
| `mbway.authorize` / `capture` (sync + async) | ✅ | ⚠️ skip — channel needs *Auth & Capture* | — |
| `multibanco.create_reference` (sync + async) | ✅ | ✅ | ✅ |
| `multibanco.get_info` (sync + async) | ✅ | ✅ | — |
| `credit_card.create_payment` (sync + async, 3DS) | ✅ | ✅ Playwright drives Shift4 + Credorax | — |
| `credit_card.authorize` / `capture` (sync + async) | ✅ | ✅ | — |
| `credit_card.create_subscription` / `charge_subscription` (sync + async) | ✅ | ✅ | — |
| `credit_card.list_subscriptions` / `get_subscription` / `edit_subscription` / `revoke_subscription` (sync + async) | ✅ | ✅ | — |
| `apple_pay.create_payment` (sync + async) | ✅ | ✅ hosted flow (`redirectUrl`); native token path needs a real Wallet device | — |
| `google_pay.create_payment` (sync + async) | ✅ | ✅ hosted flow (`redirectUrl`); native token path needs a real Google Pay device | — |
| `pay_by_link.create_payment` (sync + async) | ✅ | ✅ URL only | ✅ |
| `refunds.refund` (sync + async) | ✅ | ✅ | ✅ |
| `refunds.get` (sync + async) | ✅ | ✅ | ✅ |
| Webhooks v2.0 (POST + HMAC, cleartext **and** AES-256-CBC encrypted) | ✅ | ✅ | ✅ |
| Refund webhook (`method="RB:PT"`, links via `original_transaction_id`) | ✅ | — | ✅ |
| Webhooks v1.0 (legacy GET) | ✅ | — | — |
| HTTP transport (retry, audit hook, PII redaction, form-urlencoded support) | ✅ | — | — |

Discovered in production and now mapped: `"Canceled"` (US 1-L spelling) → `CANCELLED`,
`"REFUNDED"` (uppercase) → `REFUNDED`, `"RB:PT"` → method `"refund"`. Multibanco
refunds settle async (`"Pendente"` → `"Reembolsado"` later via webhook). Pay By
Link expiry is **silent** — no webhook, link becomes a generic 404 page; track
`expires_at` yourself.

Planned: Direct Debit, Payshop, Cofidis, Floa, PIX, Pagaqui, Paysafecard.

## Installation

```bash
pip install eupago      # or: uv add eupago
```

- **PyPI:** <https://pypi.org/project/eupago/>
- **Python:** 3.9 – 3.13
- **Dependencies:** [httpx](https://www.python-httpx.org/) and [Pydantic v2](https://docs.pydantic.dev/) — nothing else
- **Typed:** ships a `py.typed` marker (PEP 561) — full IDE autocomplete and `mypy` support
- **Optional extras:** `pip install eupago[crypto]` to decrypt AES-256-CBC webhooks; `eupago[e2e]` for Playwright-driven 3DS tests

## Quick Start

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,  # False for production
)

# MB WAY — direct mobile payment
payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="912345678",  # 9-digit Portuguese MB WAY number
)

print(payment.transaction_id)  # "txn-abc-123"
print(payment.status)          # PaymentStatus.PENDING
print(payment.amount)          # Decimal("49.90")
```

```python
# Multibanco — entity + reference for ATM/homebanking
ref = client.multibanco.create_reference(
    order_id="ORD-2026-002",
    amount=Decimal("99.00"),
)
print(ref.entity, ref.reference)   # "12345", "999888777"
```

## Async Support

Every method has an async variant — same client, `_async` suffix:

```python
async with EupagoClient(api_key="...", sandbox=True) as client:
    payment = await client.mbway.create_payment_async(
        order_id="ORD-2026-001",
        amount=Decimal("49.90"),
        phone_number="912345678",
    )
```

## Auth & Capture (MB WAY)

For two-step payments (authorize first, capture later):

```python
auth = client.mbway.authorize(
    order_id="ORD-002",
    amount=Decimal("120.00"),
    phone_number="912345678",
)

captured = client.mbway.capture(
    transaction_id=auth.transaction_id,
    amount=Decimal("120.00"),
)
```

## Webhooks

Configure the secret once on the client; `client.webhooks.parse` handles both
cleartext **and** AES-256-CBC encrypted payloads — the SDK auto-detects from
the headers:

```python
client = EupagoClient(
    api_key="…",
    webhook_secret="…",   # the channel's "Chave Criptográfica"
)

# v2.0 — POST with HMAC signature; decrypts automatically if the channel encrypts
event = client.webhooks.parse(body=request.body, headers=request.headers)

# v1.0 — legacy GET query string
event = client.webhooks.parse(query_params=dict(request.query_params))

print(event.order_id)   # "ORD-2026-001"
print(event.status)     # PaymentStatus.PAID
print(event.amount)     # Decimal("49.90")
print(event.method)     # "mbway"
```

The module-level `eupago.webhooks.parse_webhook(...)` is still available as
an escape hatch for multi-channel cases that need to pick a secret per call.

## Error Handling

All errors inherit from `EupagoError` with typed subclasses:

```python
from eupago import EupagoClient, AuthenticationError, PaymentError, NetworkError

try:
    payment = client.mbway.create_payment(...)
except AuthenticationError:
    # Invalid API key
    ...
except PaymentError as e:
    print(e.status_code, e.error_code, e.message)
except NetworkError:
    # Timeout, connection refused
    ...
```

## Configuration

```python
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    webhook_secret="…",     # The channel's Chave Criptográfica (HMAC + AES key)
    sandbox=True,           # Use sandbox environment (default: False)
    timeout=10.0,           # Request timeout in seconds (default: 10)
    max_retries=3,          # Retry failed GET requests (default: 3)
    # OAuth credentials for management endpoints (refunds, transactions)
    client_id="...",
    client_secret="...",
)

# Audit hook — log every API call to your DB / observability stack
client.set_audit_hook(
    lambda request, response, duration_ms: log_api_call(request, response, duration_ms)
)
```

## Why This SDK

- **Fully typed** — `mypy --strict` passes, `py.typed` marker included. Full autocomplete in VS Code and PyCharm.
- **Sync + Async** — one client, no separate packages. httpx powers both.
- **Decimal amounts** — no floating-point surprises with money.
- **Safe retries** — GET requests retry with exponential backoff + jitter. POSTs never retry (no idempotency keys = risk of duplicate payments).
- **PII redaction** — phone, email and NIF are auto-redacted from logs.
- **Webhook verification** — HMAC-SHA256 constant-time signature; AES-256-CBC decryption when the channel encrypts. Both schemes verified against real eupago payloads.
- **Unified vocabulary** — eupago's API has two generations with inconsistent field names (`valor`/`amount`, `chave`/`ApiKey`). The SDK normalizes everything to consistent English.
- **Exception hierarchy** — catch `PaymentError`, `NetworkError`, or `EupagoError`. Each carries `status_code`, `error_code` and `message`.

## Development

```bash
git clone https://github.com/bilouro/eupago-python.git
cd eupago-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Run checks:

```bash
ruff check .          # lint
ruff format .         # format
mypy src/             # type check (strict)
pytest                # tests with coverage (≥85% enforced)
```

The default `pytest` runs unit tests only. Live integration tests against the
sandbox live under `tests/integration/` — see `tests/integration/infra/README.md`
for the Terraform-managed AWS receiver they need.

## Contributing

PRs are welcome — especially for new payment methods on the roadmap, framework
recipes, docs improvements, or anything that makes the SDK easier to adopt.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## Production use / Consulting

This is a community SDK. If you're integrating it into a production system and
want **prioritised features, custom payment methods, audit support, or hands-on
help with eupago's quirks**, you can reach me at **consulting@bilouro.com** —
happy to help on a paid consulting basis.

For general questions, file an issue.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open
public issues for security bugs.

## License

[MIT](LICENSE) — use it however you want.
