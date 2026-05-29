# eupago

[![PyPI version](https://img.shields.io/pypi/v/eupago)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago)](https://pypi.org/project/eupago/)
[![CI](https://github.com/bilouro/eupago-python/actions/workflows/test.yml/badge.svg)](https://github.com/bilouro/eupago-python/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-mypy--strict-blue)](https://mypy.readthedocs.io/)
[![Docs](https://img.shields.io/badge/docs-bilouro.github.io-blue)](https://bilouro.github.io/eupago-python/)

The first Python SDK for [eupago](https://www.eupago.com), Portugal's payment gateway.
MB WAY, Multibanco, and more — in 5 lines of Python.

**[Documentation (PT/EN)](https://bilouro.github.io/eupago-python/)** | [Examples](examples/) | [API Reference](https://bilouro.github.io/eupago-python/api/)

> **Community SDK** — not affiliated with or endorsed by eupago.
> For official integrations, visit [eupago.com](https://www.eupago.com/integrations/api-payment-gateway).

## Status

What's implemented and verified end-to-end against the eupago sandbox today
(every method exercised by an integration test that actually marks a payment
as Paid in the sandbox backoffice and validates the captured webhook):

| Area | Status |
|---|---|
| **MB WAY** — `create_payment`, `authorize`, `capture` (sync + async) | ✅ Live-validated |
| **Multibanco** — `create_reference`, `get_info` (sync + async) | ✅ Live-validated |
| **Webhooks 2.0** — POST, HMAC signature, both cleartext **and** AES-256-CBC encrypted | ✅ Live-validated |
| **Webhooks 1.0** — legacy GET | ✅ Implemented |
| Core: typed errors, retries, sync+async, audit hook, PII redaction | ✅ |

Planned (see [roadmap in CLAUDE.md](CLAUDE.md)): Credit Card, Apple/Google Pay,
Direct Debit, Refunds, Payshop, Cofidis, Floa, PIX, Pay By Link.

## Installation

```bash
pip install eupago
```

Requires Python 3.9+. Runtime deps: [httpx](https://www.python-httpx.org/)
and [Pydantic v2](https://docs.pydantic.dev/). Add the `crypto` extra
(`pip install eupago[crypto]`) only if you receive encrypted webhooks.

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
help with eupago's quirks**, you can reach me at **bilouro@bilouro.com** —
happy to help on a paid consulting basis.

For general questions, file an issue.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open
public issues for security bugs.

## License

[MIT](LICENSE) — use it however you want.
