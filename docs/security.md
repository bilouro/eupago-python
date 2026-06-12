# Security guide

What actually matters, security-wise, when you take payments through
eupago with this SDK. Short on theory, long on the specific mistakes
that cost money.

## Card data: you don't have it, keep it that way

With eupago, the card form, the 3-D Secure challenge, and the Apple
Pay / Google Pay sheets are all **hosted by eupago** (or by the card
networks). The PAN never touches your server — which is what keeps your
PCI DSS exposure in **SAQ A** territory, the lightest self-assessment
there is.

The corollary: **never proxy or re-implement the card form** to make
the checkout "seamless". The moment card numbers flow through your
backend, you inherit the full PCI compliance burden. Redirect to
`payment_url`, let eupago do its job, wait for the webhook.

The same logic applies to your database: there is no schema in which
storing card numbers is the right call. (The
[Persisting payments](recipes/persisting-payments.md) recipe stores
ids, amounts and statuses — nothing card-shaped.)

## Know your credentials and their blast radius

You hold up to three secrets. They unlock different doors:

| Credential | Unlocks | If it leaks |
|---|---|---|
| **API key** (`api_key`) | Creating payments on one channel | Attacker can create junk payment requests in your name — annoying, not directly lucrative |
| **OAuth pair** (`client_id` / `client_secret`) | The whole Management API: **refunds**, transaction listing, subscription edit/revoke — across **all** your channels | Attacker can refund your money to wallets they control. This is the crown-jewel secret |
| **Webhook key** ("Chave Criptográfica") | Verifying/decrypting webhooks (HMAC + AES-256-CBC) | Attacker can forge webhooks that pass signature checks → fake "Paid" events |

Practical rules:

- All three live in **environment variables or a secrets manager** —
  never in code, never in the database, never in the repo. The SDK
  reads them at client construction; nothing else needs them.
- The OAuth pair **expires after 1 year** and can be revoked instantly
  in the backoffice (*A Minha Conta → Credenciais*). Calendar the
  rotation; don't discover the expiry in production.
- The webhook key is rotatable in the channel's *Webhooks 2.0* panel.
  If you ever suspect a leak, rotate it first — it is the cheapest one
  to rotate.
- Sandbox and production credentials are different worlds. Never let a
  production key into a `.env.example`, a CI log, or a developer
  laptop's shell history.

## The webhook endpoint is your attack surface

Anyone who discovers your webhook URL can POST to it. The classic
attack is exactly as dumb as it sounds: send `{"status": "Paid"}` and
hope the shop ships. Your defence is layered, and the SDK does the
hard part:

1. **Verify before you parse.** `client.webhooks.parse()` checks the
   HMAC signature (and decrypts, for encrypted channels) before
   returning anything. A payload that fails raises
   `WebhookSignatureError` — treat it as hostile: log it (redacted),
   quarantine it, change nothing.
2. **Idempotency.** eupago may redeliver. Hash the raw body and make
   the second delivery a no-op (see the
   [recipe's `on_webhook()`](recipes/persisting-payments.md#3-on_webhook-the-only-place-state-becomes-paid)).
3. **Verify the money.** Signature valid ≠ business valid. Check that
   the webhook's amount and currency match what you stored when you
   created the payment, *then* fulfil.
4. **HTTPS only**, obviously — the webhook body contains customer PII.

See [Signature verification](webhooks/signature.md) for the wire-level
details of what is signed and how.

## The redirect is not a receipt

`success_url` is where you send the customer's *browser* after a hosted
flow. It proves nothing:

- The customer can bookmark it and revisit it.
- An attacker can navigate straight to it without paying.
- The payment can still fail *after* the redirect (3DS edge cases).

Render something friendly there ("we're confirming your payment…"),
but the **only** events that flip an order to paid are a
signature-verified webhook or an authenticated poll of eupago's API.
Never `fulfil_order()` from a GET on `success_url`.

## PII: redact at every boundary

Webhook payloads and some API responses carry phone numbers, emails
and names. Two boundaries to defend:

- **Logs.** The SDK's own logger (`eupago`) auto-redacts phone, email
  and NIF patterns — that protection is built in (and is why you should
  not log eupago payloads through your own logger "for convenience").
- **Storage.** If you persist raw payloads for audit, redact them on
  the way in with the public helper:

```python
from eupago.utils import redact_pii

stored = redact_pii(webhook_payload)
# {"customer": {"email": "***EMAIL***", "phone": "***PHONE***"}, ...}
```

Pair redaction with **retention**: raw payloads should have an expiry
date (a `purge_after` column, or DynamoDB TTL). The financial facts —
amounts, statuses, transaction ids — are not PII and can live forever;
the payloads around them don't have to. This combination (minimal
data, redacted payloads, bounded retention) is most of your GDPR
story for the payments table.

## Make history tamper-evident

Your payment **event log** is what you'll reach for in a dispute. It
is only trustworthy if it cannot be quietly edited:

- The application's DB role gets `INSERT` but **not** `UPDATE`/`DELETE`
  on the events table (or the IAM equivalent on DynamoDB).
- Cancelled/failed payments are a *status*, not a deleted row.
- Backups are encrypted and actually restorable — test it once.

## Identifiers leak more than you think

- Generate `order_id` from a UUID, not a sequence. It appears in URLs,
  webhooks and emails; `ORD-000042` tells the world your sales volume
  and invites enumeration of your endpoints.
- Treat `payment_url` as a capability: anyone holding the link can see
  the amount and (for Pay By Link) pay it. Don't log it, don't index it.

## Checklist

- [ ] Card form / wallet sheets: hosted by eupago, never proxied
- [ ] Secrets in env/secret manager; OAuth rotation calendared (1 year)
- [ ] Webhook handler: verify → quarantine on failure → dedup → amount
      check → transition
- [ ] `success_url` renders a "confirming…" page; fulfilment only via
      webhook/poll
- [ ] Raw payloads stored via `redact_pii()` + bounded retention
- [ ] Event log append-only by grant/policy
- [ ] `order_id` non-sequential
