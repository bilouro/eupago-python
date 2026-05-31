# eupago Python SDK

[![PyPI version](https://img.shields.io/pypi/v/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://github.com/bilouro/eupago-python/blob/main/LICENSE)

The first Python SDK for [eupago](https://www.eupago.com), the Portuguese payment gateway.

!!! warning "Community SDK"
    This is an independent open-source project, not affiliated with or endorsed by eupago.

## Quickstart

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="your-key", sandbox=True)

payment = client.mbway.create_payment(
    order_id="ORD-001",
    amount=Decimal("49.90"),
    phone_number="912345678",
)

print(payment.transaction_id)  # "txn-abc-123"
print(payment.status)          # PaymentStatus.PENDING
```

## Payment Methods

| Method | Description | Module |
|---|---|---|
| **[MB WAY](payments/mbway.md)** | Mobile payment via push notification (5 min approval) | `client.mbway` |
| **[Multibanco](payments/multibanco.md)** | ATM / online-banking reference, paid 1–30 days later | `client.multibanco` |
| **[Credit Card](payments/credit-card.md)** | Hosted card form with 3D-Secure / OTP — supports auth+capture and recurring subscriptions | `client.credit_card` |
| **[Apple Pay](payments/apple-pay.md)** | Apple Wallet token for iOS apps and Safari | `client.apple_pay` |
| **[Google Pay](payments/google-pay.md)** | Google Pay token for Android apps and Chrome | `client.google_pay` |
| **[Pay By Link](payments/pay-by-link.md)** | Single hosted URL — customer picks the method (MB WAY, Multibanco, Card, Apple/Google Pay, Cofidis…) | `client.pay_by_link` |
| **[Refunds](payments/refund.md)** | Total or partial refunds for any paid transaction (OAuth) | `client.refunds` |

Webhooks (cleartext **and** AES-256-CBC encrypted) and v1.0 / v2.0 parsing are
covered by `client.webhooks.parse(...)` — see [Webhooks](webhooks/index.md).

## Why this SDK?

- **Sync + Async** — same client, `_async` suffix for async methods
- **Fully typed** — `mypy --strict`, full IDE autocomplete
- **Decimal** — never float for money
- **Bilingual** — documentation in Portuguese and English
- **Webhooks** — parsing + HMAC-SHA256 verification
- **Safe retries** — GET only, POST never retries (duplicate payment risk)

## Next steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Installation**

    ---

    Install and configure in 2 minutes

    [:octicons-arrow-right-24: Get started](getting-started/index.md)

-   :material-credit-card:{ .lg .middle } **Payments**

    ---

    Which method should you use? Decision guide

    [:octicons-arrow-right-24: Payments](payments/index.md)

-   :material-webhook:{ .lg .middle } **Webhooks**

    ---

    Receive payment notifications

    [:octicons-arrow-right-24: Webhooks](webhooks/index.md)

-   :material-flask:{ .lg .middle } **Recipes**

    ---

    Complete guides for FastAPI, Django, Flask

    [:octicons-arrow-right-24: Recipes](recipes/index.md)

</div>
