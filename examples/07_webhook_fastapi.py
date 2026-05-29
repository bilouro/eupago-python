"""
Webhook handler — FastAPI completo.

Recebe notificações da eupago quando um pagamento é concluído.
Suporta v1.0 (GET, legacy) e v2.0 (POST com HMAC, recomendado).
O ``client.webhooks.parse`` lida automaticamente com payloads em claro ou
encriptados (AES-256-CBC) — a deteção é feita pelos headers.

Configurar no backoffice eupago:
  URL: https://a-tua-app.pt/webhooks/eupago
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from eupago import EupagoClient, PaymentStatus

app = FastAPI()
client = EupagoClient(
    api_key=os.environ["EUPAGO_API_KEY"],
    webhook_secret=os.environ.get("EUPAGO_WEBHOOK_SECRET"),
    sandbox=os.environ.get("EUPAGO_SANDBOX", "false").lower() == "true",
)


@app.post("/webhooks/eupago")
async def webhook_v2(request: Request) -> JSONResponse:
    """Webhook v2.0 — POST com verificação HMAC (recomendado)."""
    body = await request.body()
    headers = dict(request.headers)

    event = client.webhooks.parse(body=body, headers=headers)

    print("Pagamento recebido:")
    print(f"  Pedido:  {event.order_id}")
    print(f"  Status:  {event.status}")
    print(f"  Método:  {event.method}")
    print(f"  Valor:   {event.amount} {event.currency}")

    if event.status == PaymentStatus.PAID:
        # Actualizar encomenda como paga na base de dados
        # await update_order(event.order_id, paid=True)
        pass

    # Retornar 200 — obrigatório, senão eupago reenvia
    return JSONResponse({"status": "ok"})


@app.get("/webhooks/eupago")
async def webhook_v1(request: Request) -> JSONResponse:
    """Webhook v1.0 — GET com query parameters (legacy)."""
    event = client.webhooks.parse(query_params=dict(request.query_params))

    print(f"Pagamento (v1): {event.order_id} → {event.status}")

    return JSONResponse({"status": "ok"})


# Correr:
#   uvicorn examples.07_webhook_fastapi:app --port 8000
