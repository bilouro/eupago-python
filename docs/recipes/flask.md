# Flask

Complete eupago SDK integration with [Flask](https://flask.palletsprojects.com/).

## Installation

```bash
pip install eupago flask
```

## Full example

```python
"""eupago + Flask — MB WAY payment + webhook."""

import os
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request

from eupago import EupagoClient, PaymentStatus
from eupago.exceptions import (
    EupagoError,
    SignatureError,
    ValidationError,
)
from eupago.webhooks import parse_webhook

app = Flask(__name__)

# ── Configuration ─────────────────────────────────────────────

API_KEY = os.environ["EUPAGO_API_KEY"]
WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")
SANDBOX = os.environ.get("EUPAGO_SANDBOX", "true").lower() == "true"

client = EupagoClient(api_key=API_KEY, sandbox=SANDBOX)


# ── Route: create payment ────────────────────────────────────

@app.route("/payments/mbway", methods=["POST"])
def create_mbway_payment():
    """Create an MB WAY payment."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    order_id = data.get("order_id")
    phone_number = data.get("phone_number")

    try:
        amount = Decimal(str(data.get("amount", "")))
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    try:
        result = client.mbway.create_payment(
            order_id=order_id,
            amount=amount,
            phone_number=phone_number,
        )
    except ValidationError as e:
        return jsonify({"error": str(e)}), 422
    except EupagoError as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({
        "transaction_id": result.transaction_id,
        "status": result.status.value,
        "amount": str(result.amount),
    })


# ── Route: webhook v2.0 (POST) ───────────────────────────────

@app.route("/eupago/callback", methods=["POST"])
def eupago_webhook_v2():
    """Receive v2.0 webhook (POST with HMAC signature)."""
    try:
        event = parse_webhook(
            body=request.get_data(),
            headers=dict(request.headers),
            webhook_secret=WEBHOOK_SECRET,
        )
    except SignatureError:
        return jsonify({"error": "Invalid signature"}), 403

    if event.status == PaymentStatus.PAID:
        # TODO: update order in the database
        app.logger.info(
            "Payment confirmed: order=%s amount=%s %s",
            event.order_id,
            event.amount,
            event.currency,
        )
    elif event.status == PaymentStatus.EXPIRED:
        # TODO: mark order as expired
        app.logger.info("Payment expired: order=%s", event.order_id)

    return jsonify({"status": "ok"}), 200


# ── Route: webhook v1.0 (GET) ────────────────────────────────

@app.route("/eupago/callback", methods=["GET"])
def eupago_webhook_v1():
    """Receive v1.0 webhook (GET with query params) — legacy compatibility."""
    event = parse_webhook(query_params=request.args.to_dict())

    if event.status == PaymentStatus.PAID:
        # TODO: update order in the database
        app.logger.info(
            "Payment confirmed (v1): order=%s amount=%s",
            event.order_id,
            event.amount,
        )

    return jsonify({"status": "ok"}), 200


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=8000)
```

## Running

```bash
export EUPAGO_API_KEY="xxxx-xxxx-xxxx-xxxx-xxxx"
export EUPAGO_WEBHOOK_SECRET="your-secret"
export EUPAGO_SANDBOX="true"

flask run --port 8000
# or
python app.py
```

## Testing with curl

### Create payment

```bash
curl -X POST http://localhost:8000/payments/mbway \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-001", "amount": "49.90", "phone_number": "912345678"}'
```

### Simulate v2.0 webhook

```bash
curl -X POST http://localhost:8000/eupago/callback \
  -H "Content-Type: application/json" \
  -d '{"transactions": {"identifier": "ORD-001", "amount": {"value": 49.90}, "status": "Paid", "trid": 123}}'
```

## Notes

!!! info "GET + POST on the same route"
    Flask allows registering the same route with different methods. The v1.0 webhook (GET) and v2.0 (POST) share the `/eupago/callback` path.

!!! warning "Production"
    Never use `app.run()` in production. Use a WSGI server like [Gunicorn](https://gunicorn.org/):

    ```bash
    pip install gunicorn
    gunicorn app:app --bind 0.0.0.0:8000 --workers 4
    ```

!!! tip "request.get_data() vs request.data"
    The SDK needs the body as `bytes`. Use `request.get_data()` which returns raw bytes, instead of `request.data` which may be affected by prior parsing.
