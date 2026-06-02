# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.2] - 2026-06-02

Metadata + discoverability release. No SDK behaviour changes.

### Improved
- **PyPI metadata**: longer, keyword-rich `description`; expanded `keywords` (24 entries); added `Intended Audience`, `Natural Language`, `Topic`, `Framework`, and `Pydantic` classifiers; promoted dev-status to *4 - Beta*; added `Source`, `Discussions`, `Releases`, `Funding`, and a Portuguese-docs URL to `project.urls`; added author/maintainer email.
- **README**: rewrote the lede with the SDK's positioning and value props so the Google snippet pulls a useful summary instead of a one-liner.
- **mkdocs SEO**: enabled the Material **social** plugin (auto-generates Open Graph cards per page), added a long `site_description`, `site_author`, `copyright`. JSON-LD `SoftwareApplication` structured data added to the EN and PT landing pages. Added a `robots.txt` pointing at the sitemap.
- **GitHub repo**: added 15 topics (python, payments, mbway, multibanco, portugal, eupago, sdk, payment-gateway, fintech, api-client, pay-by-link, webhook, async, typed, stripe-alternative) and a longer repo description so the GitHub card itself ranks.
- Added `.github/FUNDING.yml` so the Sponsor button shows up.

## [0.5.1] - 2026-05-31

### Fixed
- **Python 3.9 compatibility**: added `eval_type_backport>=0.2` as a conditional dependency for Python <3.10. Without it, Pydantic v2 fails at model instantiation when evaluating `X | None` annotations on 3.9 (`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`). v0.5.0 was published without this fix and was effectively unusable on 3.9 despite the classifier claiming support.
- **CI workflow** (`.github/workflows/test.yml`) — was referenced by the README CI badge since day one but never existed. Now runs `ruff check`, `ruff format --check`, `mypy --strict` and `pytest -m "not integration"` on Python 3.9–3.13.
- **README** aligned with the sibling `vendus` package: bilingual docs link ("English · Português"), Installation section as a bullet list with the explicit PyPI URL.

## [0.5.0] - 2026-05-31

First production-validated release. MB WAY, Multibanco, Pay By Link and
Refunds were exercised against a live eupago production channel
(`Destrezàvolta`) with real money — 5 transactions paid and 3 refunds
emitted, all webhooks captured and verified through the SDK. Several
real wire-shape bugs surfaced and were fixed.

### Added
- **Subscription management** on `client.credit_card` — four new methods covering the full `/api/management/v1.02/subscriptions` + `/creditcard/edit` surface that the eupago backoffice uses (sync + async):
  - `list_subscriptions()` — returns every subscription on the channel.
  - `get_subscription(subscription_id)` — full detail incl. `nextCollectionDate` and current `autoProcess` / `collectionDay`.
  - `edit_subscription(subscription_id, collection_day=..., auto_process=...)` — changes the billing schedule. With `auto_process=True` eupago bills the registered card itself on every `collection_day` of the period — no need to call `charge_subscription`. Sends as `application/x-www-form-urlencoded`, which the SDK transport now supports.
  - `revoke_subscription(subscription_id)` — cancels an active subscription (raises `SUBSCRIPTION_NOT_FOUND` on `Pendente`).
  - All four take the **integer** `subscriptionId` from the backoffice URL — not the hex `eupagoToken` (`charge_subscription` still takes the hex). The list response does not include the integer ID today; this is documented as a known eupago UX gap.
- **HTTP transport** now accepts a `data=` parameter for `application/x-www-form-urlencoded` bodies (with the Content-Type override). Used by `edit_subscription`.
- **`EupagoClient(management_bearer=...)`** — inject a pre-obtained Bearer for the `/api/management/*` endpoints (refunds, transactions, …). Bypasses the OAuth `client_id`/`client_secret` flow. Useful for tests/scripts where the caller already has a token, e.g. from the eupago backoffice login. Production callers should still prefer OAuth.
- New live integration test `tests/integration/test_refund_live.py` that pays an MB WAY transaction, captures the webhook, then calls `client.refunds.refund(...)` end-to-end and asserts `REFUNDED` + a real `refundId` in the response. Uses `management_bearer` from the backoffice helper as the temporary auth path until eupago issues OAuth credentials.

### Added
- **`client.refunds.get(refund_id)`** (sync + async) — `GET /api/management/v1.02/refund/{refundId}`. Returns the refund's current state (`identifier`, `reference`, `status`). Particularly useful for Multibanco refunds, which settle asynchronously (`status: "pendente"` until the bank transfer clears, then `"Reembolsado"`).
- **`eupago.utils.bic_for_pt_iban(iban)`** — helper that maps a Portuguese IBAN's bank code (positions 5–8) to the corresponding BIC. Covers the major retail banks in Portugal (~99% of consumer accounts). Returns `None` for niche banks. Built because Multibanco refunds require a `bic` argument and eupago doesn't expose a lookup API for it.
- **`WebhookEvent.original_transaction_id`** — populated on refund webhooks (`method="refund"`) with the trid of the original payment being refunded. Lets callers correlate the refund back to the original payment without keeping their own mapping. eupago sends this as `originalTrid` in the webhook payload.

### Docs
- **Pay By Link behaviour learned from prod smoke tests (2026-05-31):**
  - When the customer completes a Pay By Link payment, the webhook fires as the **chosen method's** webhook (e.g. `method="mbway"`), not a generic "paybylink" event. Your handler doesn't need Pay By Link special-casing — treat the webhook like any direct payment of that method.
  - When a Pay By Link expires unpaid (`expires_at` passes with no payment started), **no webhook fires**. This is different from MB WAY's direct push (which does fire an `"Expired"` webhook). Track expiry from your own clock.
- **Multibanco refund actually requires `bic` even though docs say optional** — `client.refunds.refund(...)` without `bic` returns `BIC_INVALID` on Multibanco transactions in production. Updated `docs/payments/refund.md` and `examples/12_refund.py` to make `bic` mandatory in Multibanco refund examples (with `BCOMPTPL` for Millennium BCP as the canonical example). Also documented that Multibanco refunds settle asynchronously — the sync response is `"Pendente"`, the settlement webhook arrives later (sometimes hours).

### Fixed
- **Refund webhook support** — the eupago documentation says no webhook fires on refunds. **In practice it does** (confirmed live in production, 2026-05-31): an async webhook arrives with `method="RB:PT"`, `status="REFUNDED"` (uppercase, distinct from the synchronous response's `"Reembolsado"`), and an `originalTrid` field. The SDK now maps `RB:PT` → `"refund"`, `"REFUNDED"` → `PaymentStatus.REFUNDED`, and surfaces the original trid via `WebhookEvent.original_transaction_id`. Without these mappings the refund webhook fell through to `method="rb:pt"` + `status=PENDING`, silently dropping the actual state.
- **Status normalization** for cancelled MB WAY: eupago webhooks use the US spelling `"Canceled"` (single L) for transactions the customer rejected on the MB WAY app — confirmed live in production on 2026-05-31. The SDK now maps `Canceled` / `Cancelled` / `Pending` / `Pendente` / `Reembolsado` to the right `PaymentStatus`; previously these fell through to `PaymentStatus.PENDING` (silent loss of state). Added new live smoke-test script (`scripts/prod_smoke_test.py`) used to discover this.
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
