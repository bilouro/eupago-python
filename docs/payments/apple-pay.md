# Apple Pay

## What it is

Apple Wallet payment. The eupago SDK supports it in two ways:

- **Hosted flow (recommended for web):** you call `create_payment` and
  redirect the customer's browser to the `payment_url` eupago returns.
  eupago serves the Apple Pay sheet, handles the wallet handshake and
  notifies you via webhook. **No Apple Developer account required on
  your side** — eupago is the merchant.
- **Native flow (for mobile apps or web with your own Merchant ID):**
  you obtain a `PKPaymentToken` via the Apple Pay JS API or iOS SDK
  and pass it to `create_payment`. eupago decrypts it server-side and
  charges the card directly — no redirect.

The hosted flow is the right choice for nearly every web app. Reach for
the native flow only when you need the in-page sheet (no redirect) or
already have your own Apple Pay Merchant ID.

## Hosted flow — example

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# No apple_pay_token — hosted flow.
payment = client.apple_pay.create_payment(
    order_id="ORD-AP-001",
    amount=Decimal("39.90"),
    success_url="https://shop.example/checkout/ok",
    error_url="https://shop.example/checkout/fail",
)

# Redirect the customer's browser here:
return redirect(payment.payment_url)
```

Final status arrives via webhook (see [Webhooks](../webhooks/index.md)):

```python
event = client.webhooks.parse(body=request.body, headers=request.headers)
if event.status == PaymentStatus.PAID:
    fulfil_order(event.order_id)
```

## Activation in the eupago backoffice

Sandbox: ask eupago support to enable Apple Pay on your demo channel
(self-service is not yet available). Production: requires a separate
adhesion form approved by eupago compliance — see
[the eupago Google Pay / Apple Pay article](https://customer.support.eupago.com/servicedesk/customer/portal/2/article/1953857539).

!!! warning "Sandbox limitation (as of 2026-06-12)"
    On `sandbox.eupago.pt` the hosted Apple Pay sheet opens and
    immediately closes: eupago's merchant-validation endpoint
    (`POST /api/extern/applepay/merchant/{id}`) returns
    `400 BAD_REQUEST`, so the page aborts the `ApplePaySession`
    before any wallet authentication. `create_payment` →
    `redirectUrl` works fine; only the sheet handshake is broken,
    server-side. Reported to eupago. No card is ever charged — the
    session dies before Touch ID / Face ID.

## Native flow — advanced

When you want the in-page Apple Pay sheet (no redirect), drive Apple Pay
on the client and forward the resulting token to the SDK:

```python
# Captured from window.ApplePaySession on the browser, or the iOS PassKit
# delegate. The SDK treats it as an opaque string.
apple_pay_token = '{"paymentMethod": "...", "paymentData": {"version": "EC_v1", ...}}'

payment = client.apple_pay.create_payment(
    order_id="ORD-AP-002",
    amount=Decimal("39.90"),
    apple_pay_token=apple_pay_token,
)
```

This path requires:

- An Apple Developer account with an Apple Pay Merchant ID.
- Domain verification for the eupago Apple Pay flow.
- A real Wallet-enabled device for live verification.

## Refund

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    amount=Decimal("39.90"),
)
```

See [Refunds](refund.md) for OAuth setup.

## Notes

- When `apple_pay_token` is omitted, the SDK does not send `applePayToken`
  in the request — that's how eupago knows to serve the hosted sheet.
- Body shape mirrors the verified v1.02 credit-card contract.
- See the runnable
  [`09_apple_pay.py`](https://github.com/bilouro/eupago-python/blob/main/examples/09_apple_pay.py).
