# Instalação e Quickstart

## Instalação

```bash
pip install eupago
```

Requer Python 3.9+. As únicas dependências são [httpx](https://www.python-httpx.org/) e [Pydantic v2](https://docs.pydantic.dev/).

## Primeiro pagamento

### 1. Obtém a API Key

No backoffice eupago, vai a **Canais** > **Listagem de Canais** e copia a API Key do canal desejado.

### 2. Cria o client

```python
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,  # False para produção
)
```

### 3. Cria um pagamento MB WAY

```python
from decimal import Decimal

payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="351#912345678",
)

print(payment.transaction_id)  # ID da transação
print(payment.status)          # PaymentStatus.PENDING
```

O cliente recebe uma notificação push no telemóvel e tem 5 minutos para aprovar.

### 4. Recebe o webhook

Quando o cliente paga, a eupago envia um webhook ao teu servidor:

```python
from eupago.webhooks import parse_webhook

event = parse_webhook(
    body=request.body,
    headers=request.headers,
    webhook_secret="o-teu-secret",
)

if event.status == PaymentStatus.PAID:
    # Actualizar encomenda como paga
    ...
```

## Async

Todos os métodos têm variante async — mesmo client, suffix `_async`:

```python
async with EupagoClient(api_key="...", sandbox=True) as client:
    payment = await client.mbway.create_payment_async(
        order_id="ORD-001",
        amount=Decimal("49.90"),
        phone_number="351#912345678",
    )
```

## Próximos passos

- [Configuração](configuration.md) — sandbox, timeout, OAuth, audit hook
- [Qual método escolher?](../payments/index.md) — guia de decisão
- [Webhooks](../webhooks/index.md) — receber notificações
