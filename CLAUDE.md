# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Unofficial Python SDK for the [eupago](https://www.eupago.com) payment gateway (Portugal). Published as `eupago` on PyPI. Covers MB WAY, Multibanco, Credit Card, Apple/Google Pay, Payshop, Cofidis, Floa, PIX, Direct Debit, and more.

## Build & Development

```bash
pip install -e ".[dev]"
pre-commit install
```

## Testing

```bash
pytest                              # all unit tests (coverage ≥85% enforced)
pytest tests/unit/test_mbway.py     # single module
pytest -m "not integration"         # skip sandbox tests
pytest -k "test_create_payment"     # single test by name
```

## Linting & Type Checking

```bash
ruff check .        # lint
ruff format .       # auto-format
mypy src/           # strict type checking
```

## Architecture

**src layout** (`src/eupago/`) — PEP 621, hatchling build.

- **`_client.py`** — `EupagoClient`: entry point. Services lazy-loaded via properties. Supports context manager (sync + async).
- **`_http.py`** — `HttpTransport`: httpx wrapper. Retry with exponential backoff + jitter on GETs only. POST never retries (no idempotency keys in eupago). Audit hook support.
- **`_auth.py`** — `ApiKeyAuth` (header or body injection) + `OAuthAuth` (auto-refresh Bearer token). Auth method selected per-request by each service.
- **`_config.py`** — Base URLs (sandbox vs production), API version prefix, timeout defaults.
- **`_logging.py`** — PII redaction filter for phone numbers, emails, NIF.
- **`exceptions.py`** — `EupagoError` base → `ApiError` (with `status_code`, `error_code`) → `PaymentError`, `NotFoundError`, `RateLimitError`, etc. `WebhookError` → `SignatureError`, `DecryptionError`.
- **`models/`** — Pydantic v2. `PaymentResult`, `PaymentStatus` (enum), `Customer`, `WebhookEvent`. All amounts are `Decimal`.
- **`services/`** — One module per payment method. `BaseService` provides `_request()` / `_request_async()` with auth injection. Pattern: sync method + `_async` suffix variant.
- **`webhooks/`** — `parse_webhook()` handles both v1.0 (GET query params) and v2.0 (POST JSON with HMAC signature + optional AES encryption).

## Key Design Constraints

- **Decimal, not float** for monetary amounts.
- **Retry only GETs** — POST never retries (eupago has no idempotency keys).
- **No PII in logs** — phone, email, NIF redacted.
- **`sandbox=True`** switches base URL; no hardcoded URLs.
- **Python ≥3.9** — use `from __future__ import annotations` for modern type syntax.
- **Two eupago API generations** — legacy (`/clientes/rest_api/`, body auth) and modern v1.02 (`/api/v1.02/`, header auth). Services abstract this transparently.

## Naming Convention

The SDK normalizes eupago's inconsistent field names:
- `valor` / `payment.amount` → `amount` (Decimal)
- `id` / `payment.identifier` → `order_id`
- `alias` → `phone_number`
- `chave` / ApiKey header → `api_key`
- `estado` / HTTP status / webhook status → `PaymentStatus` enum
