# Webhooks

## Como funcionam

Quando um pagamento e confirmado (ex: o cliente aprova no MB WAY, ou paga a referencia Multibanco), a eupago envia uma notificacao HTTP ao teu servidor — o **webhook**.

O teu servidor deve:

1. Receber o pedido
2. Verificar a autenticidade (assinatura HMAC no v2.0)
3. Actualizar a encomenda na base de dados
4. Responder com **HTTP 200**

```
Cliente paga ──► eupago processa ──► Webhook ao teu servidor
                                          │
                                          ▼
                                    Actualiza encomenda
```

!!! warning "Retorna sempre HTTP 200"
    Se o teu servidor nao retornar 200, a eupago vai reenviar o webhook:

    - A cada **2 minutos**, ate **3 tentativas**
    - Depois, **a cada hora** durante **24 horas**

    Apos esse periodo, o webhook e descartado.

---

## Versoes do webhook

A eupago suporta duas versoes de webhook. Recomendamos a v2.0.

### v1.0 — Legacy (GET)

O webhook e enviado como **GET** com query parameters:

| Parametro | Descricao | Exemplo |
|---|---|---|
| `valor` | Montante pago | `49.90` |
| `identificador` | Order ID (o teu) | `ORD-2026-001` |
| `transacao` | ID da transacao eupago | `78901` |
| `referencia` | Referencia de pagamento | `999888777` |
| `entidade` | Entidade Multibanco | `12345` |
| `mp` | Metodo de pagamento | `MW:PT` |
| `chave_api` | API key (para validacao) | `xxxx-xxxx` |
| `data` | Data do pagamento | `2026-05-26` |

### v2.0 — Recomendado (POST + HMAC)

O webhook e enviado como **POST** com body JSON e assinatura HMAC-SHA256 no header `X-Signature`.

```json
{
  "transactions": {
    "entity": 12345,
    "reference": 999888777,
    "identifier": "ORD-2026-001",
    "method": "Mbway",
    "amount": {"value": 49.90, "currency": "EUR"},
    "fees": {"value": 0.35, "currency": "EUR"},
    "date": "2026-05-26T14:30:00Z",
    "trid": 78901,
    "status": "Paid"
  },
  "channel": {"name": "main-channel"}
}
```

**Headers:**

| Header | Descricao |
|---|---|
| `X-Signature` | HMAC-SHA256 do body com o teu webhook secret |
| `X-Initialization-Vector` | IV para decriptacao AES (opcional) |
| `Content-Type` | `application/json` |

!!! tip "Usa sempre v2.0"
    A v2.0 inclui assinatura HMAC para prevenir falsificacao, e opcionalmente encriptacao AES-256-CBC para proteger dados sensiveis em transito.

---

## Usar o SDK

O SDK abstrai ambas as versoes com uma unica funcao: `parse_webhook()`.

### Webhook v2.0 (POST)

```python
from eupago.webhooks import parse_webhook
from eupago.models import PaymentStatus

event = parse_webhook(
    body=request.body,
    headers=dict(request.headers),
    webhook_secret="o-teu-secret",  # Verifica HMAC automaticamente
)

if event.status == PaymentStatus.PAID:
    print(f"Encomenda {event.order_id} paga: {event.amount} {event.currency}")
```

### Webhook v1.0 (GET)

```python
from eupago.webhooks import parse_webhook

event = parse_webhook(query_params=dict(request.query_params))

print(f"Encomenda {event.order_id} paga: {event.amount} {event.currency}")
```

### O objecto `WebhookEvent`

Ambas as versoes retornam um `WebhookEvent` com campos normalizados:

| Campo | Tipo | Descricao |
|---|---|---|
| `order_id` | `str \| None` | O teu order ID |
| `transaction_id` | `str \| None` | ID da transacao eupago |
| `reference` | `str \| None` | Referencia de pagamento |
| `entity` | `str \| None` | Entidade Multibanco |
| `amount` | `Decimal \| None` | Montante pago |
| `currency` | `str` | Moeda (default `"EUR"`) |
| `status` | `PaymentStatus` | Estado normalizado |
| `method` | `str \| None` | Metodo de pagamento normalizado |
| `paid_at` | `str \| None` | Data/hora do pagamento |
| `channel` | `str \| None` | Canal eupago |
| `fee` | `Decimal \| None` | Comissao eupago |

---

## Configurar no backoffice

1. Acede ao [backoffice eupago](https://sandbox.eupago.pt) (sandbox) ou [producao](https://clientes.eupago.pt)
2. Vai a **Canais** > **Listagem de Canais**
3. Selecciona o canal desejado
4. Em **Callback URL**, introduz o URL do teu endpoint (ex: `https://loja.pt/eupago/callback`)
5. Escolhe a versao do webhook (recomendamos v2.0)
6. Se v2.0, copia o **Webhook Secret** para a tua aplicacao

!!! warning "HTTPS obrigatorio"
    A eupago so envia webhooks para URLs HTTPS em producao. Em desenvolvimento, usa ferramentas como [ngrok](https://ngrok.com/) para expor o teu servidor local.

---

## Proximos passos

- [Verificacao de assinatura](signature.md) — HMAC-SHA256 e encriptacao AES
- [Receitas](../recipes/index.md) — exemplos completos com FastAPI, Django, Flask
