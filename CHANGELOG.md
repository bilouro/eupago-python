# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **MB WAY**: `create_payment`, `authorize`, `capture` (sync + async). Live-verified against the eupago sandbox.
- **Multibanco**: `create_reference`, `get_info` (sync + async). Live-verified, including the paid `info` response.
- **Credit Card**: `create_payment`, `authorize`, `capture`, `create_subscription`, `charge_subscription` (sync + async). `create` live-verified against the sandbox; full 3D-Secure paid flow uses the official test card (`4018810000150015`, OTP `0101`) and is documented but not yet driven by an automated test (Playwright is the next step).
- **`EupagoClient(webhook_secret=...)`** and a **`client.webhooks.parse(body, headers)`** namespace (Stripe-style configuration on the client; the module-level `parse_webhook` stays as the escape hatch).
- **Encrypted webhook support** (AES-256-CBC) — auto-detected from `X-Initialization-Vector` and the `{"data": "..."}` body shape, validated end-to-end against a real encrypted payload from the sandbox. New `crypto` extra (`pip install eupago[crypto]`).
- `currency` parameter on MB WAY create/authorize (defaults to `EUR`).
- Comprehensive typed exception hierarchy with `status_code`, `error_code` (now `int | str | None`) and `message`.
- PII redaction filter (`_logging.py`) — phone, email, NIF.
- Audit hook (`client.set_audit_hook(...)`).
- Headless integration test suite (`tests/integration/`) with a Terraform-managed AWS webhook receiver (Lambda + API Gateway + DynamoDB) and a sandbox-backoffice automation helper, so every paid flow is exercised end-to-end without manual clicks.

### Changed
- Auth header is now **`Authorization: ApiKey <key>`** (not a header named `ApiKey`). Affects every v1.02 endpoint.
- Error responses with **string** `code` (e.g. `APIKEY_MISSING`) no longer crash the error path; the message in the `text` field is surfaced.
- MB WAY create request: `amount` is now `{value, currency}` (object), and the phone goes in `payment.customerPhone` (not `alias`).
- Webhook v2.0 parsing: `transaction` (singular) — the previously-assumed `transactions` (plural) was incorrect.
- Webhook signature: `X-Signature` is **base64**(HMAC-SHA256), not hex. For encrypted channels the HMAC payload is the **base64 ciphertext string** (the value of `data`); for cleartext channels it is the **raw body**. Both schemes are auto-detected.
- AES key for encrypted webhooks: the channel's *Chave Criptográfica* is the **32-byte AES-256 key directly** (UTF-8 bytes). It is not a passphrase to derive with SHA-256.
- Multibanco `get_info`: paid detection now uses the `estado_referencia == "paga"` field and the `pagamentos` array (the old `data_pagamento`-only heuristic returned PENDING for actually-paid references).
- Multibanco `order_id` is read from `identificador` (not `id`).
- v0.6.0 roadmap entry refocused to **webhook docs/recipes only** — no framework adapters, matching Stripe/Mollie.

### Removed
- The premature `Credit Card`, `Apple Pay` and `Google Pay` scaffolding (services, tests, examples, docs) — they were ahead of the v0.3.0 phase. They will return when that milestone starts.

### Fixed
- `MB WAY` request body shape against the real v1.02 API (confirmed via sandbox).
- Webhook decryption error message now points at the `crypto` extra.

## [0.0.1] - 2026-05-26
- Initial scaffolding.
