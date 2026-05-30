# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`EupagoClient(management_bearer=...)`** — inject a pre-obtained Bearer for the `/api/management/*` endpoints (refunds, transactions, …). Bypasses the OAuth `client_id`/`client_secret` flow. Useful for tests/scripts where the caller already has a token, e.g. from the eupago backoffice login. Production callers should still prefer OAuth.
- New live integration test `tests/integration/test_refund_live.py` that pays an MB WAY transaction, captures the webhook, then calls `client.refunds.refund(...)` end-to-end and asserts `REFUNDED` + a real `refundId` in the response. Uses `management_bearer` from the backoffice helper as the temporary auth path until eupago issues OAuth credentials.

### Fixed
- **Refund** body shape: was `{value, currency, motivo}`, eupago expects `{amount, reason}` (plus optional `iban`/`bic` for non-MB WAY / non-Card transactions). The old shape returned `AMOUNT_MISSING`. Response parser now reads `refundId` correctly (live-verified: `{"transactionStatus":"Success","refundId":"2788","status":"Reembolsado"}`). Parameter renamed from `value` to `amount` to match the wire field.
- **MB WAY** request body now includes the required `countryCode` (default `"351"`) and `customerPhone` on every endpoint, not only `create`. Without `countryCode` the `authorize` endpoint returns `CUSTOMERPHONE_MISSING` / `BAD_REQUEST` even though the value was present, because the eupago spec ties the two together.
- **MB WAY capture** body shape: was `{"payment": {"amount": X}}`, eupago expects `{"payment": {"value": X, "currency": "EUR"}}`. The old body returned `AMOUNT_MISSING`. Fixed and asserted by unit test.
- **Credit Card capture** now sends the full payment body (amount object + URLs) — the previous empty body returned `AMOUNT_MISSING`. New required parameter `amount`; optional `success_url`/`error_url`/`back_url`/`customer`/`order_id`.
- **Credit Card subscription**:
  - `create_subscription` now wraps the request with the required `subscription` block (`date`, `autoProcess`, `collectionDay`, `periodicity`, `limitDate`). Without it the endpoint returns 500 BAD_REQUEST. New optional parameters: `start_date`, `periodicity` (default `"Mensal"`), `collection_day` (default `1`), `limit_date` (default 1 year out), `auto_process` (default `False`).
  - Response parser now reads `subscriptionID` and `referenceSubs` (the names the subscription endpoint actually uses) in addition to `transactionID`/`reference`. The `subscriptionID` is mapped to `PaymentResult.transaction_id` so it can be passed straight to `charge_subscription`.
  - `charge_subscription` takes `recurrent_id: str` (eupago returns a hex string, not an int) and accepts the required `success_url`/`error_url`/`back_url` + optional `days_to_capture`.

### Added
- **MB WAY**: `create_payment`, `authorize`, `capture` (sync + async). Live-verified against the eupago sandbox.
- **Multibanco**: `create_reference`, `get_info` (sync + async). Live-verified, including the paid `info` response.
- **Credit Card**: `create_payment`, `authorize`, `capture`, `create_subscription`, `charge_subscription` (sync + async). Full 3D-Secure flow is end-to-end validated by a Playwright integration test using the official sandbox test card (`4018810000150015`, OTP `0101`) — Playwright drives the Shift4 form and the Credorax ACS challenge, and the test asserts the `Paid` webhook lands in the test receiver.
- **Refunds**: `client.refunds.refund` (sync + async). OAuth-authenticated against `/api/management/v1.02/refund/{trid}`; live verification requires `client_id` / `client_secret` on the channel and a paid transaction to refund. Per the eupago docs, **refunds do not fire webhooks** — verify via the response or the management transactions endpoint. OAuth credentials are issued by eupago support on request (customer.support.eupago.com); they are not the API key and are not self-service in the backoffice.
- **Apple Pay**: `client.apple_pay.create_payment` (sync + async). Forwards the `PKPaymentToken` from Apple Wallet to `payment.applePayToken`; same verified v1.02 body shape as credit card. Live verification needs a real Wallet-enabled device.
- **Google Pay**: `client.google_pay.create_payment` (sync + async). Same pattern with `googlePayToken`. Live verification needs a real Google Pay-enabled device.
- **Pay By Link**: `client.pay_by_link.create_payment` (sync + async). Generates an eupago-hosted checkout URL where the customer picks the payment method (MB WAY, Multibanco, Card, Apple/Google Pay, Cofidis…). Supports optional `expires_at`, `shipping`, `products` line items, and `customer` notification. Body shape verified against the v1.02 reference and live against the sandbox (`tests/integration/test_pay_by_link_live.py`).
- New `e2e` optional extra (`pip install eupago[e2e]`) — Playwright dep for the headless 3DS test.
- **`EupagoClient(webhook_secret=...)`** and a **`client.webhooks.parse(body, headers)`** namespace (Stripe-style configuration on the client; the module-level `parse_webhook` stays as the escape hatch).
- **Encrypted webhook support** (AES-256-CBC) — auto-detected from `X-Initialization-Vector` and the `{"data": "..."}` body shape, validated end-to-end against a real encrypted payload from the sandbox. New `crypto` extra (`pip install eupago[crypto]`).
- `currency` parameter on MB WAY create/authorize (defaults to `EUR`).
- Comprehensive typed exception hierarchy with `status_code`, `error_code` (now `int | str | None`) and `message`.
- PII redaction filter (`_logging.py`) — phone, email, NIF.
- Audit hook (`client.set_audit_hook(...)`).
- Headless integration test suite (`tests/integration/`) with a Terraform-managed AWS webhook receiver (Lambda + API Gateway + DynamoDB) and a sandbox-backoffice automation helper, so every paid flow is exercised end-to-end without manual clicks.
- Lifecycle examples covering every payment method (`examples/01`–`12`): MB WAY (payment, auth+capture), Multibanco (reference, get_info), Credit Card (payment, auth+capture, subscription+charge), Apple Pay, Google Pay, Pay By Link, and a standalone Refund flow — each ending with the refund pattern so the full pay → refund cycle is visible end to end.

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
