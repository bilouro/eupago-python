# Django

Integracao completa do SDK eupago com [Django](https://www.djangoproject.com/).

## Instalacao

```bash
pip install eupago django
```

## Estrutura do projecto

```
myshop/
├── myshop/
│   ├── settings.py
│   └── urls.py
└── payments/
    ├── __init__.py
    ├── urls.py
    └── views.py
```

## Configuracao (settings.py)

Adiciona as variaveis de configuracao ao teu `settings.py`:

```python
# myshop/settings.py

import os

# eupago
EUPAGO_API_KEY = os.environ["EUPAGO_API_KEY"]
EUPAGO_WEBHOOK_SECRET = os.environ.get("EUPAGO_WEBHOOK_SECRET", "")
EUPAGO_SANDBOX = os.environ.get("EUPAGO_SANDBOX", "true").lower() == "true"
```

## Views (views.py)

```python
"""eupago + Django — pagamento MB WAY + webhook."""

import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from eupago import EupagoClient, PaymentStatus
from eupago.exceptions import (
    EupagoError,
    SignatureError,
    ValidationError,
)
from eupago.webhooks import parse_webhook

# ── Client (reutilizado entre requests) ───────────────────────

client = EupagoClient(
    api_key=settings.EUPAGO_API_KEY,
    sandbox=settings.EUPAGO_SANDBOX,
)


# ── View: criar pagamento ────────────────────────────────────

@require_POST
def create_mbway_payment(request):
    """Cria um pagamento MB WAY."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    order_id = data.get("order_id")
    phone_number = data.get("phone_number")

    try:
        amount = Decimal(str(data.get("amount", "")))
    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "Invalid amount"}, status=400)

    try:
        result = client.mbway.create_payment(
            order_id=order_id,
            amount=amount,
            phone_number=phone_number,
        )
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=422)
    except EupagoError as e:
        return JsonResponse({"error": str(e)}, status=502)

    return JsonResponse({
        "transaction_id": result.transaction_id,
        "status": result.status.value,
        "amount": str(result.amount),
    })


# ── View: webhook v2.0 (POST) ────────────────────────────────

@csrf_exempt
@require_POST
def eupago_webhook_v2(request):
    """Recebe webhook v2.0 (POST com assinatura HMAC)."""
    try:
        event = parse_webhook(
            body=request.body,
            headers=dict(request.headers),
            webhook_secret=settings.EUPAGO_WEBHOOK_SECRET,
        )
    except SignatureError:
        return JsonResponse({"error": "Invalid signature"}, status=403)

    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        # Order.objects.filter(order_id=event.order_id).update(status="paid")
        pass
    elif event.status == PaymentStatus.EXPIRED:
        # TODO: marcar encomenda como expirada
        pass

    return JsonResponse({"status": "ok"})


# ── View: webhook v1.0 (GET) ─────────────────────────────────

@require_GET
def eupago_webhook_v1(request):
    """Recebe webhook v1.0 (GET com query params) — compatibilidade legacy."""
    event = parse_webhook(query_params=request.GET.dict())

    if event.status == PaymentStatus.PAID:
        # TODO: actualizar encomenda na base de dados
        pass

    return JsonResponse({"status": "ok"})
```

## URLs (urls.py)

### App URLs (payments/urls.py)

```python
from django.urls import path

from payments import views

urlpatterns = [
    path("payments/mbway/", views.create_mbway_payment, name="create-mbway"),
    path("eupago/callback/", views.eupago_webhook_v2, name="eupago-webhook-v2"),
    path("eupago/callback/v1/", views.eupago_webhook_v1, name="eupago-webhook-v1"),
]
```

### Project URLs (myshop/urls.py)

```python
from django.urls import include, path

urlpatterns = [
    path("", include("payments.urls")),
]
```

## Correr

```bash
export EUPAGO_API_KEY="xxxx-xxxx-xxxx-xxxx-xxxx"
export EUPAGO_WEBHOOK_SECRET="o-teu-secret"
export EUPAGO_SANDBOX="true"

python manage.py runserver
```

## Testar com curl

### Criar pagamento

```bash
curl -X POST http://localhost:8000/payments/mbway/ \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORD-001", "amount": "49.90", "phone_number": "912345678"}'
```

### Simular webhook v2.0

```bash
curl -X POST http://localhost:8000/eupago/callback/ \
  -H "Content-Type: application/json" \
  -d '{"transactions": {"identifier": "ORD-001", "amount": {"value": 49.90}, "status": "Paid", "trid": 123}}'
```

## Notas

!!! warning "CSRF"
    O endpoint de webhook usa `@csrf_exempt` porque a eupago nao envia tokens CSRF. A seguranca e garantida pela verificacao HMAC.

!!! tip "Django REST Framework"
    Se usas DRF, podes converter as views para `APIView` ou `@api_view`. O SDK funciona exactamente da mesma forma — so muda como acedes ao body e headers.

!!! info "Async com Django"
    Django 4.1+ suporta views async. Para usar `create_payment_async()`:

    ```python
    async def create_mbway_payment(request):
        result = await client.mbway.create_payment_async(...)
        return JsonResponse({...})
    ```

    Requer um servidor ASGI (ex: Daphne, Uvicorn).
