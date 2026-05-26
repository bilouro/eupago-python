"""Webhook handler — FastAPI example."""

import os

from fastapi import FastAPI, Request

from eupago.webhooks import parse_webhook

app = FastAPI()
WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")


@app.post("/eupago/callback")
async def eupago_callback(request: Request) -> dict[str, str]:
    body = await request.body()
    headers = dict(request.headers)

    event = parse_webhook(
        body=body,
        headers=headers,
        webhook_secret=WEBHOOK_SECRET,
    )

    print(f"Payment {event.order_id}: {event.status} — {event.amount} {event.currency}")

    return {"status": "ok"}


@app.get("/eupago/callback")
async def eupago_callback_v1(request: Request) -> dict[str, str]:
    event = parse_webhook(query_params=dict(request.query_params))

    print(f"Payment {event.order_id}: {event.status} — {event.amount} {event.currency}")

    return {"status": "ok"}
