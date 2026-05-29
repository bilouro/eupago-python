# FastAPI

Integracao completa do SDK eupago com [FastAPI](https://fastapi.tiangolo.com/).

## Instalacao

```bash
pip install eupago fastapi uvicorn
```

## Exemplo completo

```python
"""eupago + FastAPI — pagamento MB WAY + webhook."""

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

app = FastAPI(title="Loja com eupago")

# ── Configuracao ──────────────────────────────────────────────

API_KEY = os.environ["EUPAGO_API_KEY"]
WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")
SANDBOX = os.environ.get("EUPAGO_SANDBOX", "true").lower() == "true"

client = EupagoClient(api_key=API_KEY, sandbox=SANDBOX)


# ── Modelos de request ────────────────────────────────────────

class PaymentRequest(BaseModel):
    order_id: str
    amount: Decimal
    phone_number: str


# ── Endpoint: criar pagamento ─────────────────────────────────

@app.post("/payments/mbway")
async def create_mbway_payment(payload: PaymentRequest):
    """Cria um pagamento MB WAY."""
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
    """Recebe webhook v2.0 (POST com assinatura HMAC)."""
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

    # Processar o pagamento
    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        print(
            f"Pagamento confirmado: order={event.order_id} "
            f"amount={event.amount} {event.currency}"
        )
    elif event.status == PaymentStatus.EXPIRED:
        # TODO: marcar encomenda como expirada
        print(f"Pagamento expirado: order={event.order_id}")

    # Retornar 200 para a eupago nao reenviar
    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Endpoint: webhook v1.0 (GET) ─────────────────────────────

@app.get("/eupago/callback")
async def eupago_webhook_v1(request: Request):
    """Recebe webhook v1.0 (GET com query params) — compatibilidade legacy."""
    event = parse_webhook(query_params=dict(request.query_params))

    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        print(
            f"Pagamento confirmado (v1): order={event.order_id} "
            f"amount={event.amount}"
        )

    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Lifecycle ─────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()
```

## Correr

```bash
export EUPAGO_API_KEY="xxxx-xxxx-xxxx-xxxx-xxxx"
export EUPAGO_WEBHOOK_SECRET="o-teu-secret"
export EUPAGO_SANDBOX="true"

uvicorn app:app --reload --port 8000
```

## Testar com curl

### Criar pagamento

```bash
curl -X POST http://localhost:8000/payments/mbway \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-001", "amount": "49.90", "phone_number": "912345678"}'
```

### Simular webhook v2.0

```bash
curl -X POST http://localhost:8000/eupago/callback \
  -H "Content-Type: application/json" \
  -d '{"transactions": {"identifier": "ORD-001", "amount": {"value": 49.90}, "status": "Paid", "trid": 123}}'
```

## Notas

!!! tip "Async nativo"
    O FastAPI e async por natureza. Usa `create_payment_async()` e `await` para nao bloquear o event loop.

!!! warning "Context manager"
    O exemplo usa `@app.on_event("shutdown")` para fechar o client. Em alternativa, podes usar [lifespan](https://fastapi.tiangolo.com/advanced/events/):

    ```python
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await client.aclose()

    app = FastAPI(lifespan=lifespan)
    ```
