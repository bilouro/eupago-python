# FastAPI

Complete eupago SDK integration with [FastAPI](https://fastapi.tiangolo.com/).

## Installation

```bash
pip install eupago fastapi uvicorn
```

## Full example

```python
"""eupago + FastAPI — MB WAY payment + webhook."""

import os
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from eupago import EupagoClient, PaymentStatus
from eupago.exceptions import (
    EupagoError,
    SignatureError,
    ValidationError,
)
from eupago.webhooks import parse_webhook

app = FastAPI(title="Shop with eupago")

# ── Configuration ─────────────────────────────────────────────

API_KEY = os.environ["EUPAGO_API_KEY"]
WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")
SANDBOX = os.environ.get("EUPAGO_SANDBOX", "true").lower() == "true"

client = EupagoClient(api_key=API_KEY, sandbox=SANDBOX)


# ── Request models ────────────────────────────────────────────

class PaymentRequest(BaseModel):
    order_id: str
    amount: Decimal
    phone_number: str


# ── Endpoint: create payment ──────────────────────────────────

@app.post("/payments/mbway")
async def create_mbway_payment(payload: PaymentRequest):
    """Create an MB WAY payment."""
    try:
        result = await client.mbway.create_payment_async(
            order_id=payload.order_id,
            amount=payload.amount,
            phone_number=payload.phone_number,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except EupagoError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "transaction_id": result.transaction_id,
        "status": result.status.value,
        "amount": str(result.amount),
    }


# ── Endpoint: webhook v2.0 (POST) ────────────────────────────

@app.post("/eupago/callback")
async def eupago_webhook_v2(request: Request):
    """Receive v2.0 webhook (POST with HMAC signature)."""
    body = await request.body()
    headers = dict(request.headers)

    try:
        event = parse_webhook(
            body=body,
            headers=headers,
            webhook_secret=WEBHOOK_SECRET,
        )
    except SignatureError:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Process the payment
    if event.status == PaymentStatus.PAID:
        # TODO: update order in the database
        print(
            f"Payment confirmed: order={event.order_id} "
            f"amount={event.amount} {event.currency}"
        )
    elif event.status == PaymentStatus.EXPIRED:
        # TODO: mark order as expired
        print(f"Payment expired: order={event.order_id}")

    # Return 200 so eupago does not retry
    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Endpoint: webhook v1.0 (GET) ─────────────────────────────

@app.get("/eupago/callback")
async def eupago_webhook_v1(request: Request):
    """Receive v1.0 webhook (GET with query params) — legacy compatibility."""
    event = parse_webhook(query_params=dict(request.query_params))

    if event.status == PaymentStatus.PAID:
        # TODO: update order in the database
        print(
            f"Payment confirmed (v1): order={event.order_id} "
            f"amount={event.amount}"
        )

    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Lifecycle ─────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()
```

## Running

```bash
export EUPAGO_API_KEY="xxxx-xxxx-xxxx-xxxx-xxxx"
export EUPAGO_WEBHOOK_SECRET="your-secret"
export EUPAGO_SANDBOX="true"

uvicorn app:app --reload --port 8000
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

!!! tip "Native async"
    FastAPI is async by nature. Use `create_payment_async()` with `await` to avoid blocking the event loop.

!!! warning "Context manager"
    The example uses `@app.on_event("shutdown")` to close the client. Alternatively, you can use [lifespan](https://fastapi.tiangolo.com/advanced/events/):

    ```python
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await client.aclose()

    app = FastAPI(lifespan=lifespan)
    ```
