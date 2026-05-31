# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Unofficial Python SDK for the [eupago](https://www.eupago.com) payment gateway (Portugal). Published as `eupago` on PyPI. This is a community-driven, open-source project designed for professional adoption — companies should be able to trust this SDK in production.

The eupago API has two coexisting generations (legacy body-auth + modern v1.02 header-auth), inconsistent field naming, and three authentication methods. This SDK abstracts all of that into a clean, consistent, Pythonic interface.

## Commands

```bash
# Development setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Run checks (must all pass before commit)
ruff check .                        # lint
ruff format .                       # auto-format
mypy src/                           # strict type checking
pytest                              # tests with coverage (≥85% enforced)

# Run specific tests
pytest tests/unit/test_mbway.py     # single module
pytest -k "test_create_payment"     # single test by name
pytest -m "not integration"         # skip sandbox tests
```

---

## Architecture

### Pattern: Stripe-inspired client with Mollie-style mixins

```
EupagoClient (lazy-loads services via properties)
  └── MBWayService(BaseService)    ← one service per payment method
        ├── _request()             ← sync, auth injected by BaseService
        └── _request_async()       ← async variant
              └── HttpTransport    ← httpx wrapper with retry, timeout, audit hook
                    └── ApiKeyAuth / OAuthAuth  ← auth strategy per endpoint
```

### File Structure

```
src/eupago/
├── __init__.py          ← Public API: EupagoClient, models, exceptions, __version__
├── _client.py           ← EupagoClient — the only thing users instantiate
├── _http.py             ← HttpTransport — httpx sync+async, retry, timeout, User-Agent
├── _auth.py             ← ApiKeyAuth (header/body) + OAuthAuth (auto-refresh Bearer)
├── _config.py           ← URLs, prefixes, defaults — no magic, all constants
├── _logging.py          ← PII redaction filter (phone, email, NIF)
├── exceptions.py        ← Exception hierarchy (public API)
├── models/              ← Pydantic v2 models (public API)
│   ├── payment.py       ← PaymentResult, PaymentStatus enum, status/method maps
│   ├── customer.py      ← Customer
│   └── webhook.py       ← WebhookEvent
├── services/            ← One module per payment method
│   ├── _base.py         ← BaseService with _request/_request_async + auth injection
│   └── mbway.py         ← MBWayService (reference implementation)
├── webhooks/
│   ├── __init__.py      ← parse_webhook() — public entry point
│   ├── _parser.py       ← v1.0 (GET) + v2.0 (POST) parsing
│   └── _signature.py    ← HMAC-SHA256 verify + AES-256-CBC decrypt
└── py.typed             ← PEP 561 marker
```

### Underscore convention

- `_filename.py` = internal module, not part of public API
- `filename.py` = public module, exported in `__init__.py`

---

## Rules for Development

### R1: Naming Convention — The Unified Vocabulary

The eupago API uses inconsistent names across its two generations. The SDK normalizes EVERYTHING to a single vocabulary. **Never expose raw eupago field names to the user.**

| Concept | SDK name | eupago legacy | eupago v1.02 | Python type |
|---|---|---|---|---|
| Amount | `amount` | `valor` | `payment.amount.value` | `Decimal` |
| Currency | `currency` | — | `payment.amount.currency` | `str` (default `"EUR"`) |
| Order ID | `order_id` | `id` | `payment.identifier` | `str` |
| Reference | `reference` | `referencia` | `reference` | `str` |
| Entity | `entity` | `entidade` | `entity` | `str` |
| Transaction ID | `transaction_id` | `transacao` | `transactionID` | `str` |
| Phone number | `phone_number` | — | `payment.customerPhone` (9 digits, no country prefix) | `str` |
| Email | `email` | `email` | `customer.email` | `str` |
| Customer name | `customer_name` | — | `customer.name` | `str` |
| Success URL | `success_url` | `url_retorno` | `successUrl` | `str` |
| Error URL | `error_url` | — | `failUrl` | `str` |
| Back URL | `back_url` | — | `backUrl` | `str` |
| Callback URL | `callback_url` | — | `adminCallback` | `str` |
| Description | `description` | — | `payment.description` | `str` |
| Expiration | `expires_at` | `data_fim` | — | `datetime \| None` |
| API key | `api_key` | `chave` | header `ApiKey` | `str` |
| Webhook secret | `webhook_secret` | — | AES key | `str` |

**When adding a new payment method:** look at its API fields, find the matching SDK name in this table. If a new concept appears, add it to the table and use it consistently across ALL services.

### R2: Money is Decimal, Never Float

```python
# CORRECT
amount=Decimal("49.90")

# WRONG — float causes 49.8999... bugs
amount=49.90
```

All `amount` fields in models are `Decimal`. When building request bodies for the eupago API, convert with `float(amount)` only at the serialization boundary (inside the service method, never in models).

### R3: POST Never Retries

eupago has no idempotency keys. Retrying a POST can duplicate a payment. The `HttpTransport` enforces this:
- **GET**: retry up to `max_retries` times with exponential backoff + jitter
- **POST/PUT/DELETE**: never retry, fail immediately

This is non-negotiable. Do not add retry logic to POST requests.

### R4: Auth is Per-Endpoint, Not Global

eupago uses three auth methods depending on the endpoint:

| Endpoint type | Auth method | How the SDK handles it |
|---|---|---|
| Modern v1.02 (`/api/v1.02/...`) | `Authorization: ApiKey xxxx` header | `BaseService._default_auth = "header"` |
| Legacy (`/clientes/rest_api/...`) | `chave` in request body | Service sets `auth="body"` in `_request()` |
| Management (`/api/management/v1.02/...`) | `Bearer <token>` header | Service sets `auth="oauth"` in `_request()` |

Management Bearer can come from two sources, both wired into the same `auth="oauth"` slot via `eupago._auth`:

- **`OAuthAuth`** (`EupagoClient(client_id=…, client_secret=…)`) — production path; SDK calls `/api/auth/token` with `grant_type=client_credentials`, caches the token, refreshes on expiry.
- **`StaticBearerAuth`** (`EupagoClient(management_bearer="…")`) — test escape hatch; caller injects a Bearer they obtained elsewhere (e.g. the backoffice login flow). Bypasses the token fetch. Documented as test-mode in the README.

Each service declares its default auth type. Individual methods can override it. The user never thinks about auth — it's transparent.

### R5: Every Method Has a Sync + Async Variant

Pattern (from Stripe):

```python
class SomeService(BaseService):
    def create_payment(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = self._request("POST", PATH, json=body)
        return _parse_response(response.json(), ...)

    async def create_payment_async(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = await self._request_async("POST", PATH, json=body)
        return _parse_response(response.json(), ...)
```

- Shared logic goes in module-level functions (`_build_request_body`, `_parse_response`)
- Sync and async methods are near-identical — only `self._request` vs `await self._request_async`
- The `_async` suffix is the convention (not a separate client class)

### R6: No PII in Logs

Phone numbers, emails, and NIF are automatically redacted by `_logging.py`. Never add log statements that bypass the `eupago` logger. Never include PII in exception messages that could be displayed to end users.

### R7: Validate Before Calling the API

Catch obvious errors locally instead of wasting an API call:

```python
if amount <= 0 or amount > _MAX_AMOUNT:
    raise ValidationError(f"Amount must be between 0.01 and {_MAX_AMOUNT}")
```

Use `ValidationError` (not `ValueError`). Keep validations minimal — validate constraints documented by eupago, don't invent extra ones.

### R8: Status Normalization

The user never sees raw eupago status codes. All services convert to `PaymentStatus` enum:

```python
class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ERROR = "error"
    DECLINED = "declined"
```

Mapping is in `models/payment.py` — `normalize_status()` and `normalize_method()`. When adding a new payment method with new status codes, add them to the maps there.

### R9: Raw Response Always Available

Every `PaymentResult` includes `raw_response: dict` — the unparsed JSON from eupago. This is the escape hatch for fields the SDK doesn't model yet. Never remove this.

### R10: Examples Show the Recommended Path, Not Every Parameter

"The API supports it" ≠ "the example should show it."

Examples must show what a developer would do in a **real app** — the simplest, most correct path. Advanced/optional parameters go in a separate "Advanced" section or in the API reference, not in the main example.

Checklist before writing an example:
1. Remove every parameter that has a sensible default or is configured elsewhere (e.g., webhooks in backoffice)
2. Add inline comments explaining **what each parameter does**, not just its name
3. Read the example as a developer seeing the SDK for the first time — is it clear?
4. Compare with how Stripe/Mollie examples present the same flow

Concrete rule: `callback_url` is configured once in the eupago backoffice, not per-payment. Never show it in basic examples. `success_url`/`error_url` ARE per-payment (browser redirects) and should be shown.

### R11: Research UX, Not Just API

Before implementing a feature, study how **top SDKs present that feature to developers**, not just the raw API endpoints. The API tells you what's possible; the best SDKs tell you what's recommended.

For each new feature, check:
1. How does Stripe handle this? (stripe.com/docs)
2. What does the developer journey look like? (setup → first call → webhook → done)
3. Which parameters are "configure once" vs "pass every time"?

### R12: Testing Discipline — Live-Validate, Then Guard With Unit

This is the discipline that found four real wire-shape bugs (MB WAY `countryCode`, MB WAY capture body, Credit Card capture body, Refund body) that unit-only testing had missed.

**Two layers, both required:**

| Layer | Where | Runs on | Job |
|---|---|---|---|
| Unit (`respx` mocks httpx) | `tests/unit/test_<service>.py` | Every commit / CI | Assert the **exact wire body** + behaviour. Coverage gate ≥85%. |
| Live (real sandbox + AWS receiver) | `tests/integration/test_<service>_live.py` | Manually, env-var-gated | Prove the SDK actually works end-to-end against the real upstream. |

**Unit tests must assert the wire body, not just the return value.** This is non-negotiable. Three of the four bugs above slipped past tests that only asserted `result.transaction_id == "..."`. Pattern:

```python
body = json.loads(route.calls[0].request.content)
assert body == {"payment": {"value": 49.90, "currency": "EUR"}}
```

**Live tests use `@pytest.mark.integration`**, skip automatically when env vars are missing, and follow the *skip-with-reason* rule: when the upstream channel doesn't have a feature provisioned, skip with a clear reason — never let a test pass silently when it didn't really validate:

```python
try:
    return client.foo.bar(...)
except ApiError as e:
    if e.error_code == "BAD_REQUEST":
        pytest.skip(
            "Channel does not have <feature> enabled (eupago returned BAD_REQUEST). "
            "The SDK body shape was sent but the endpoint refuses the channel — "
            "re-run on a channel with <feature> provisioned."
        )
    raise
```

**Honesty rule for the README/CHANGELOG/roadmap.** Use the **per-operation status matrix** (Unit / Live columns). Never claim "service.* live-validated" when only `create_payment` was. Three operations skipping with documented reasons is honest and fine; calling them all "Done" is the trap.

**Live-validate as discovery.** When live testing reveals an SDK bug: fix the SDK → add a unit test that asserts the corrected wire body → the live test passes. That's how the SDK becomes by-the-book against the real API rather than against the docs.

---

## How to Add a New Payment Method

Follow `services/mbway.py` as the reference implementation. Steps:

### 1. Create the service file

```
src/eupago/services/{method_name}.py
```

### 2. Structure the service

```python
from __future__ import annotations

from decimal import Decimal
from typing import Any

from eupago._config import API_PREFIX  # or LEGACY_PREFIX for old endpoints
from eupago.exceptions import ValidationError
from eupago.models.payment import PaymentResult, PaymentStatus
from eupago.services._base import BaseService

_MAX_AMOUNT = Decimal("99999")
_PATH_CREATE = f"{API_PREFIX}/{method}/create"


def _build_request_body(...) -> dict[str, Any]:
    """Build the eupago API request body. Validates inputs."""
    ...

def _parse_response(data: dict[str, Any], ...) -> PaymentResult:
    """Convert raw eupago response to PaymentResult."""
    ...


class SomeService(BaseService):
    # For legacy endpoints:
    # _default_auth = "body"

    def create_payment(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = self._request("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), ...)

    async def create_payment_async(self, ...) -> PaymentResult:
        body = _build_request_body(...)
        response = await self._request_async("POST", _PATH_CREATE, json=body)
        return _parse_response(response.json(), ...)
```

### 3. Register in the client

In `_client.py`, add a property:

```python
@property
def new_method(self) -> NewMethodService:
    return self._get_service("new_method", NewMethodService)  # type: ignore[no-any-return]
```

### 4. Export in `__init__.py`

Only if the service exposes new public models. Services themselves are accessed via `client.method_name`, not imported directly.

### 5. Add tests (R12 — read it first)

Two test files per service:

**Unit** — `tests/unit/test_{method_name}.py`:
- Mock with `respx`; never call the real API.
- **Assert the exact request body** sent on the wire (`json.loads(route.calls[0].request.content)`), not just the return value.
- Cover: success path, validation errors, API error handling, async variant.
- Add JSON fixtures in `tests/fixtures/` when responses are large.

**Live** — `tests/integration/test_{method_name}_live.py`:
- Mark with `@pytest.mark.integration` (deselected by default).
- Skip via `pytest.mark.skipif` when required env vars (`EUPAGO_API_KEY`, `EUPAGO_WEBHOOK_TABLE`, `EUPAGO_WEBHOOK_SECRET`, etc.) are missing.
- Use the `BackofficeSession` helper (`tests/integration/sandbox_backoffice.py`) to mark-paid; assert the captured webhook from the AWS receiver (DynamoDB).
- For features the demo channel doesn't have provisioned, use `pytest.skip(...)` with a clear reason rather than failing the suite.

### 6. Update `services/__init__.py`

Add the import.

---

## eupago API Reference (Quick Lookup)

### Base URLs
- Sandbox: `https://sandbox.eupago.pt`
- Production: `https://clientes.eupago.pt`

### Endpoint Prefixes
- Modern: `/api/v1.02/{method}/{action}`
- Legacy: `/clientes/rest_api/{method}/{action}`
- Management: `/api/management/v1.02/{resource}`
- Auth: `/api/auth/token`

### Authentication
- **ApiKey header**: `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx` (most v1.02 endpoints — the `ApiKey ` prefix is part of the `Authorization` value, NOT a header named `ApiKey`)
- **Body auth**: `{"chave": "xxxx-xxxx-xxxx-xxxx-xxxx", ...}` (Multibanco, Payshop, Paysafecard)
- **OAuth Bearer**: `Authorization: Bearer <token>` (management endpoints)

### Response Error Codes (legacy)
`0` = success, `-7` = inactive service, `-8` = invalid reference, `-9` = wrong values, `-10` = invalid key, `-11` = payment not found, `-12` = invalid alias

### Webhook v2.0 Format

Verified against the real sandbox (note: `transaction` is **singular**; values are
often strings).

**Signature** (`X-Signature`, base64-encoded HMAC-SHA256) — the bytes signed
depend on whether the channel encrypts:
- **cleartext channel:** `base64(HMAC-SHA256(raw_body, secret))`
- **encrypted channel:** `base64(HMAC-SHA256(ciphertext_b64_string, secret))`
  where `ciphertext_b64_string` is the value of the `data` field of the body.

The HMAC key is the channel's "Chave Criptográfica" used as **UTF-8 bytes**.

**Encryption** (when enabled): AES-256-CBC with PKCS7 padding.
- **AES key = the channel's "Chave Criptográfica" as raw bytes (32 bytes).** It is
  **not** a passphrase — the backoffice generates a key of exactly the right
  size. Do NOT pass it through `SHA-256` or any KDF.
- IV: base64 in header `X-Initialization-Vector` (16 bytes after decode).
- Encrypted body shape: `{"data": "<base64 ciphertext>"}`.
- After decryption, the plaintext is the same `{"channel": ..., "transaction": ...}` JSON below.

```json
{
  "channel": {"account": "demo-account", "name": "demo-channel"},
  "transaction": {
    "entity": "12345", "reference": "999888777",
    "identifier": "ORD-001", "method": "PC:PT",
    "amount": {"value": "49.90000", "currency": "EUR"},
    "fees": {"value": 0.8364, "currency": "EUR"},
    "date": "2026-05-26T14:30:00",
    "trid": "78901", "status": "Paid", "local": "demo"
  }
}
```

### Payment Methods & Endpoints

| Method | Endpoint | Auth |
|---|---|---|
| MB WAY | `POST /api/v1.02/mbway/create` | header |
| MB WAY authorize | `POST /api/v1.02/mbway/authorize` | header |
| MB WAY capture | `POST /api/v1.02/mbway/capture/{txId}` | header |
| Multibanco | `POST /clientes/rest_api/multibanco/create` | body |
| Credit Card | `POST /api/v1.02/creditcard/create` | header |
| Apple Pay | `POST /api/v1.02/applepay/create` | header |
| Google Pay | `POST /api/v1.02/googlepay/create` | header |
| Payshop | `POST /clientes/rest_api/payshop/create` | body |
| PIX | `POST /api/v1.02/pix/create` | header |
| Cofidis | `POST /api/v1.02/cofidis/create` | header |
| Floa | `POST /api/v1.02/floa/create` | header |
| Direct Debit | `POST /api/v1.02/directdebit/authorization` | header |
| Pay By Link | `POST /api/v1.02/paybylink/create` | header |
| Pagaqui | `POST /api/v1.02/pagaqui/create` | header |
| Paysafecard | `POST /clientes/rest_api/paysafecard/create` | body |
| Refund | `POST /api/management/v1.02/refund/{trid}` | oauth |
| Transactions | `GET /api/management/v1.02/transactions` | oauth |
| Subscriptions list | `GET /api/management/v1.02/subscriptions` | oauth |
| Subscription detail | `GET /api/management/v1.02/subscriptions/{subscriptionId}` | oauth |
| Subscription edit | `PUT /api/management/v1.02/creditcard/edit/{subscriptionId}` | oauth (**form-urlencoded body**) |
| Subscription revoke | `POST /api/management/v1.02/subscriptions/revoke/{subscriptionId}` | oauth |
| Pay By Link detail | `GET /api/management/v1.02/paybylink/details/{paybylinkId}` | oauth |

**Important on identifiers**: subscription endpoints use the **integer `subscriptionId`** (e.g. `4756`, visible in the backoffice URL when editing a subscription), NOT the hex `eupagoToken` (`c20e18387478…`) that `create_subscription` returns and `charge_subscription` accepts. The two are different identifiers for the same resource.

**Important on body shapes**: `PUT /creditcard/edit/{id}` expects `application/x-www-form-urlencoded`, not JSON. The `BaseService._request` / `HttpTransport.request` both accept a `data=` kwarg that overrides the default `Content-Type` for this case.

---

## Roadmap

| Version | Scope | Status |
|---|---|---|
| **v0.1.0** | MB WAY + webhooks + core | **Done** |
| **v0.2.0** | Multibanco | **Done** |
| **v0.3.0** | Credit Card + Apple/Google Pay | **Done** |
| **v0.4.0** | Refunds (OAuth) + Pay By Link | **Done** (refund live-verification pending OAuth creds from eupago support) |
| v0.5.0 | Direct Debit, Payshop, Cofidis, Floa, PIX, Pagaqui, Paysafecard | — |
| v0.6.0 | Webhook docs/recipes only — `parse_webhook` stays the public API; **no framework adapters** (keeps the SDK framework-agnostic, like Stripe/Mollie) | — |
| v0.7.0 | CLI tool + dry-run mode | — |
| v1.0.0 | Stable API, full docs | — |

---

## Quality Standards

- `ruff check .` — zero warnings
- `ruff format --check .` — fully formatted
- `mypy src/` with `--strict` — zero errors
- `pytest` — all pass, coverage ≥85%
- All four checks must pass before any commit
- Python ≥3.9 compatibility — use `from __future__ import annotations`, never `match/case` or bare `X | Y` at runtime
- Every public function has type annotations
- `py.typed` marker present — IDEs get full autocomplete
