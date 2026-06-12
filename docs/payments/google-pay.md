# Google Pay

## What it is

Google Pay payment. The eupago SDK supports it in two ways:

- **Hosted flow (recommended for web):** you call `create_payment` and
  redirect the customer's browser to the `payment_url` eupago returns.
  eupago serves the Google Pay sheet, handles the wallet handshake and
  notifies you via webhook. **No Google Pay merchant id required on
  your side** — eupago is the merchant.
- **Native flow (for mobile apps or web with your own merchant id):**
  you obtain a `PaymentData` token via the Google Pay JS API or Android
  SDK and pass it to `create_payment`. eupago decrypts it server-side
  and charges the card directly — no redirect.

The hosted flow is the right choice for nearly every web app. Reach for
the native flow only when you need the in-page sheet (no redirect) or
already have your own Google Pay merchant id.

## Hosted flow — example

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# No google_pay_token — hosted flow.
payment = client.google_pay.create_payment(
    order_id="ORD-GP-001",
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

Sandbox: ask eupago support to enable Google Pay on your demo channel
(self-service is not yet available). Production: requires a separate
adhesion form approved by eupago compliance — see
[the eupago Google Pay / Apple Pay article](https://customer.support.eupago.com/servicedesk/customer/portal/2/article/1953857539).

## Native flow — advanced

When you want the in-page Google Pay sheet (no redirect), drive Google
Pay on the client and forward the resulting token to the SDK:

```python
# Captured from PaymentsClient.loadPaymentData on the browser, or the
# Google Pay Android API. The SDK treats it as an opaque string.
google_pay_token = '{"paymentMethodData": {"tokenizationData": {"token": "..."}}}'

payment = client.google_pay.create_payment(
    order_id="ORD-GP-002",
    amount=Decimal("39.90"),
    google_pay_token=google_pay_token,
)
```

This path requires:

- A merchant configured in the Google Pay & Wallet Console.
- A real Google Pay-enabled device for live verification.

## Refund

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    amount=Decimal("39.90"),
)
```

See [Refunds](refund.md) for OAuth setup.

## Notes

- When `google_pay_token` is omitted, the SDK does not send `googlePayToken`
  in the request — that's how eupago knows to serve the hosted sheet.
- Body shape mirrors the verified v1.02 credit-card contract.
- See the runnable
  [`10_google_pay.py`](https://github.com/bilouro/eupago-python/blob/main/examples/10_google_pay.py).
