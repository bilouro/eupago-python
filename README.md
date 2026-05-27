# eupago

[![PyPI version](https://img.shields.io/pypi/v/eupago)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago)](https://pypi.org/project/eupago/)
[![CI](https://github.com/bilouro/eupago-python/actions/workflows/test.yml/badge.svg)](https://github.com/bilouro/eupago-python/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-mypy--strict-blue)](https://mypy.readthedocs.io/)
[![Docs](https://img.shields.io/badge/docs-bilouro.github.io-blue)](https://bilouro.github.io/eupago-python/)

The first Python SDK for [eupago](https://www.eupago.com), Portugal's payment gateway.
Multibanco, MB WAY, Credit Card, Apple Pay, Google Pay, and more — in 5 lines of Python.

**[Documentation (PT/EN)](https://bilouro.github.io/eupago-python/)** | [Examples](examples/) | [API Reference](https://bilouro.github.io/eupago-python/api/)

> **Community SDK** — not affiliated with or endorsed by eupago.
> For official integrations, visit [eupago.com](https://www.eupago.com/integrations/api-payment-gateway).

## Installation

```bash
pip install eupago
```

Requires Python 3.9+. No additional dependencies beyond [httpx](https://www.python-httpx.org/) and [Pydantic v2](https://docs.pydantic.dev/).

## Quick Start

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,  # False for production
)

# Request a MB WAY payment
payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="351#912345678",
)

print(payment.transaction_id)  # "txn-abc-123"
print(payment.status)          # PaymentStatus.PENDING
print(payment.amount)          # Decimal("49.90")
```

## Async Support

Every method has an async variant — same client, `_async` suffix:

```python
async with EupagoClient(api_key="...", sandbox=True) as client:
    payment = await client.mbway.create_payment_async(
        order_id="ORD-2026-001",
        amount=Decimal("49.90"),
        phone_number="351#912345678",
    )
```

## Auth & Capture

For two-step payments (authorize first, capture later):

```python
# Step 1: Authorize — customer approves on their phone
auth = client.mbway.authorize(
    order_id="ORD-002",
    amount=Decimal("120.00"),
    phone_number="351#912345678",
)

# Step 2: Capture — charge the authorized amount
captured = client.mbway.capture(
    transaction_id=auth.transaction_id,
    amount=Decimal("120.00"),
)
```

## Webhooks

Parse payment notifications from eupago — supports both v1.0 (GET) and v2.0 (POST with HMAC signature):

```python
from eupago.webhooks import parse_webhook

# v2.0 — POST with signature verification
event = parse_webhook(
    body=request.body,
    headers=request.headers,
    webhook_secret="your-secret",
)

# v1.0 — GET query parameters (legacy)
event = parse_webhook(query_params=dict(request.query_params))

print(event.order_id)   # "ORD-2026-001"
print(event.status)     # PaymentStatus.PAID
print(event.amount)     # Decimal("49.90")
print(event.method)     # "mbway"
```

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
    # Payment declined or failed
    print(e.status_code, e.error_code, e.message)
except NetworkError:
    # Timeout, connection refused
    ...
```

## Configuration

```python
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,           # Use sandbox environment (default: False)
    timeout=10.0,           # Request timeout in seconds (default: 10)
    max_retries=3,          # Retry failed GET requests (default: 3)
    # OAuth credentials for management endpoints (refunds, transactions)
    client_id="...",
    client_secret="...",
)

# Audit hook — log every API call to your database
client.set_audit_hook(
    lambda request, response, duration_ms: log_api_call(request, response, duration_ms)
)
```

## Supported Payment Methods

| Method | Status | Module |
|---|---|---|
| MB WAY | Available | `client.mbway` |
| Multibanco | Coming soon | `client.multibanco` |
| Credit Card | Coming soon | `client.credit_card` |
| Apple Pay | Coming soon | `client.apple_pay` |
| Google Pay | Coming soon | `client.google_pay` |
| Direct Debit | Coming soon | `client.direct_debit` |
| Payshop | Coming soon | `client.payshop` |
| Cofidis Pay | Coming soon | `client.cofidis` |
| Floa (BNPL) | Coming soon | `client.floa` |
| PIX / EuroPix | Coming soon | `client.pix` |
| Pay By Link | Coming soon | `client.pay_by_link` |

## Why This SDK

- **Fully typed** — `mypy --strict` passes, `py.typed` marker included. Full autocomplete in VS Code and PyCharm.
- **Sync + Async** — one client, no separate packages. httpx powers both.
- **Decimal amounts** — no floating-point surprises with money. `Decimal("49.90")`, not `49.8999...`.
- **Safe retries** — GET requests retry with exponential backoff + jitter. POST requests never retry (no idempotency keys = risk of duplicate payments).
- **PII redaction** — phone numbers, emails, and NIF are automatically redacted from logs.
- **Webhook verification** — HMAC-SHA256 constant-time signature comparison. Optional AES-256-CBC decryption for encrypted payloads.
- **Unified naming** — eupago's API has two generations with inconsistent field names (`valor`/`amount`, `chave`/`ApiKey`, `alias`/`phone`). The SDK normalizes everything to clean, consistent English.
- **Exception hierarchy** — catch `PaymentError` for declined payments, `NetworkError` for timeouts, or `EupagoError` for everything. Each error carries `status_code`, `error_code`, and `message`.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially for new payment methods.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open public issues for security bugs.

## License

[MIT](LICENSE) — use it however you want.
