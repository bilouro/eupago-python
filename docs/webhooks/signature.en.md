# Signature Verification

## HMAC-SHA256

eupago signs each v2.0 webhook with HMAC-SHA256. The `X-Signature` header contains the hex digest of the body, computed with your webhook secret.

### How it works

```
HMAC-SHA256(webhook_secret, request_body) == X-Signature header
```

### Automatic verification with the SDK

When you pass `webhook_secret` to `parse_webhook()`, verification is automatic:

```python
from eupago.webhooks import parse_webhook
from eupago.exceptions import SignatureError

try:
    event = parse_webhook(
        body=request.body,
        headers=dict(request.headers),
        webhook_secret="your-secret",
    )
except SignatureError:
    # Invalid signature — reject the request
    return Response(status_code=403)
```

If the signature does not match, the SDK raises `SignatureError`.

### Manual verification

If you need to verify manually (without the SDK):

```python
import hashlib
import hmac

def verify_eupago_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# Usage
body = request.body  # bytes
signature = request.headers["X-Signature"]
secret = "your-webhook-secret"

if not verify_eupago_signature(body, signature, secret):
    raise ValueError("Invalid signature!")
```

!!! danger "Use compare_digest"
    Never use `==` to compare hashes — it is vulnerable to timing attacks. Always use `hmac.compare_digest()`.

---

## AES-256-CBC Encryption

Optionally, eupago can encrypt the webhook body with AES-256-CBC. In this case, the body contains a `data` field with the Base64-encoded encrypted payload, and the `X-Initialization-Vector` header contains the IV.

### Requirements

Encryption requires the `cryptography` package:

```bash
pip install cryptography
```

Or install the SDK with the extra:

```bash
pip install eupago[crypto]
```

### Automatic decryption with the SDK

The SDK detects and decrypts automatically when:

1. The body contains a `data` field
2. The `X-Initialization-Vector` header is present
3. You passed `webhook_secret` to `parse_webhook()`

```python
from eupago.webhooks import parse_webhook
from eupago.exceptions import DecryptionError

try:
    event = parse_webhook(
        body=request.body,
        headers=dict(request.headers),
        webhook_secret="your-secret",
    )
    # event already contains the decrypted data
except DecryptionError as e:
    print(f"Decryption failed: {e}")
```

### Manual decryption

If you need to decrypt manually:

```python
import base64
import hashlib
import json

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


def decrypt_eupago_payload(
    encrypted_data: str,
    secret: str,
    iv_b64: str,
) -> dict:
    iv = base64.b64decode(iv_b64)
    data = base64.b64decode(encrypted_data)
    key = hashlib.sha256(secret.encode()).digest()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()

    unpadder = PKCS7(128).unpadder()
    result = unpadder.update(padded) + unpadder.finalize()

    return json.loads(result)


# Usage
body = json.loads(request.body)
iv = request.headers["X-Initialization-Vector"]
secret = "your-webhook-secret"

payload = decrypt_eupago_payload(body["data"], secret, iv)
print(payload["transactions"]["identifier"])
```

### How the key is derived

eupago uses SHA-256 of your webhook secret as the 256-bit AES key:

```
AES_key = SHA-256(webhook_secret)    # 32 bytes
```

The IV (Initialization Vector) is randomly generated for each webhook and sent in the `X-Initialization-Vector` header as Base64.

---

## Security best practices

### 1. Always verify the signature

Never process a webhook without verifying the HMAC signature. Without verification, anyone can send fake webhooks to your server.

```python
# CORRECT — verifies the signature
event = parse_webhook(body=body, headers=headers, webhook_secret=secret)

# WRONG — accepts any webhook
event = parse_webhook(body=body, headers=headers)
```

### 2. Store the secret securely

```python
import os

# CORRECT — environment variable
WEBHOOK_SECRET = os.environ["EUPAGO_WEBHOOK_SECRET"]

# WRONG — hardcoded in source code
WEBHOOK_SECRET = "abc123"
```

### 3. Use HTTPS

In production, your webhook endpoint must use HTTPS. For development, use [ngrok](https://ngrok.com/) or similar.

### 4. Respond with 200 quickly

Process the webhook asynchronously (e.g. task queue) and respond with 200 as fast as possible. If you take longer than 30 seconds, eupago considers the webhook failed.

### 5. Idempotency

eupago may resend the same webhook multiple times. Your handler must be idempotent — check if you have already processed the `transaction_id` before updating the order.

```python
event = parse_webhook(body=body, headers=headers, webhook_secret=secret)

# Check if already processed
if db.webhooks.exists(transaction_id=event.transaction_id):
    return Response(status_code=200)  # Already processed, return 200

# Process
db.orders.update(order_id=event.order_id, status="paid")
db.webhooks.insert(transaction_id=event.transaction_id)
```

### 6. Do not rely solely on the webhook

For high-value payments, verify the status directly via API in addition to the webhook:

```python
# Webhook received — confirm via API
status = client.mbway.get_status(transaction_id=event.transaction_id)
if status.status == PaymentStatus.PAID:
    # Payment confirmed
    ...
```
