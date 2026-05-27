# Flask

Integracao completa do SDK eupago com [Flask](https://flask.palletsprojects.com/).

## Instalacao

```bash
pip install eupago flask
```

## Exemplo completo

```python
"""eupago + Flask — pagamento MB WAY + webhook."""

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

# ── Configuracao ──────────────────────────────────────────────

API_KEY = os.environ["EUPAGO_API_KEY"]
WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")
SANDBOX = os.environ.get("EUPAGO_SANDBOX", "true").lower() == "true"

client = EupagoClient(api_key=API_KEY, sandbox=SANDBOX)


# ── Rota: criar pagamento ────────────────────────────────────

@app.route("/payments/mbway", methods=["POST"])
def create_mbway_payment():
    """Cria um pagamento MB WAY."""
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


# ── Rota: webhook v2.0 (POST) ────────────────────────────────

@app.route("/eupago/callback", methods=["POST"])
def eupago_webhook_v2():
    """Recebe webhook v2.0 (POST com assinatura HMAC)."""
    try:
        event = parse_webhook(
            body=request.get_data(),
            headers=dict(request.headers),
            webhook_secret=WEBHOOK_SECRET,
        )
    except SignatureError:
        return jsonify({"error": "Invalid signature"}), 403

    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        app.logger.info(
            "Pagamento confirmado: order=%s amount=%s %s",
            event.order_id,
            event.amount,
            event.currency,
        )
    elif event.status == PaymentStatus.EXPIRED:
        # TODO: marcar encomenda como expirada
        app.logger.info("Pagamento expirado: order=%s", event.order_id)

    return jsonify({"status": "ok"}), 200


# ── Rota: webhook v1.0 (GET) ─────────────────────────────────

@app.route("/eupago/callback", methods=["GET"])
def eupago_webhook_v1():
    """Recebe webhook v1.0 (GET com query params) — compatibilidade legacy."""
    event = parse_webhook(query_params=request.args.to_dict())

    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        app.logger.info(
            "Pagamento confirmado (v1): order=%s amount=%s",
            event.order_id,
            event.amount,
        )

    return jsonify({"status": "ok"}), 200


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=8000)
```

## Correr

```bash
export EUPAGO_API_KEY="xxxx-xxxx-xxxx-xxxx-xxxx"
export EUPAGO_WEBHOOK_SECRET="o-teu-secret"
export EUPAGO_SANDBOX="true"

flask run --port 8000
# ou
python app.py
```

## Testar com curl

### Criar pagamento

```bash
curl -X POST http://localhost:8000/payments/mbway \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-001", "amount": "49.90", "phone_number": "351#912345678"}'
```

### Simular webhook v2.0

```bash
curl -X POST http://localhost:8000/eupago/callback \
  -H "Content-Type: application/json" \
  -d '{"transactions": {"identifier": "ORD-001", "amount": {"value": 49.90}, "status": "Paid", "trid": 123}}'
```

## Notas

!!! info "GET + POST na mesma rota"
    O Flask permite registar a mesma rota com metodos diferentes. O webhook v1.0 (GET) e v2.0 (POST) partilham o path `/eupago/callback`.

!!! warning "Producao"
    Nunca uses `app.run()` em producao. Usa um servidor WSGI como [Gunicorn](https://gunicorn.org/):

    ```bash
    pip install gunicorn
    gunicorn app:app --bind 0.0.0.0:8000 --workers 4
    ```

!!! tip "request.get_data() vs request.data"
    O SDK precisa do body como `bytes`. Usa `request.get_data()` que retorna bytes puros, em vez de `request.data` que pode ser afectado por parsing anterior.
