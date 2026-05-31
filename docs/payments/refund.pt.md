# Reembolsos

## O que são

Reverter uma transação previamente paga — total ou parcialmente. Funciona
para qualquer método (MB WAY, Multibanco, Cartão, Apple/Google Pay,
Pay By Link, …).

Os reembolsos usam a **API de management** do eupago, que tem autenticação
distinta dos restantes endpoints.

## Webhook de reembolso (a documentação diz "não", na prática "sim")

A documentação da eupago diz que não há webhook em reembolsos. **Em
produção há** — confirmado live a 2026-05-31:

```json
{
  "transaction": {
    "method": "RB:PT",                    // reembolso
    "status": "REFUNDED",                 // maiúsculas aqui, "Reembolsado" na resposta síncrona
    "trid": "113194712",                  // o transaction_id do próprio refund
    "originalTrid": "113193247",          // o trid do pagamento que se reembolsou ← reconciliação
    "identifier": "PROD-MW-74685211ac",
    "amount": {"value": 1, "currency": "EUR"}
  }
}
```

O SDK parseia correctamente:

```python
event = client.webhooks.parse(body=request.body, headers=request.headers)
if event.method == "refund" and event.status == PaymentStatus.REFUNDED:
    # link para o pagamento original sem precisares de manter o teu mapeamento
    original_payment_id = event.original_transaction_id
```

A resposta síncrona (200/201 + ``refundId``) continua a ser a fonte de
verdade. O webhook é útil para **reconciliação** — sobretudo quando o
reembolso parte de fora do teu SDK (ex: admin no backoffice).

## Obter as credenciais OAuth

O endpoint de reembolso requer `client_id` + `client_secret`, **não** a
API Key normal:

- **Não estão disponíveis self-service no backoffice.**
- São emitidas pelo **suporte eupago a pedido** (abre um ticket em
  [customer.support.eupago.com](https://customer.support.eupago.com/) ou
  envia email para `suporte@eupago.pt`).
- O mesmo par autoriza qualquer endpoint `/api/management/...`.

Quando as tiveres, configura o client uma vez:

```python
client = EupagoClient(
    api_key="...",
    client_id="...",
    client_secret="...",
    sandbox=True,
)
```

O SDK trata do token: pede em `/api/auth/token` com
`grant_type=client_credentials`, faz cache do Bearer e renova quando
expira — não tens de fazer nada.

## Exemplo

```python
from decimal import Decimal
from eupago import EupagoClient, PaymentStatus

client = EupagoClient(
    api_key="...",
    client_id="...",
    client_secret="...",
    sandbox=True,
)

# Reembolso total (MB WAY ou Cartão — sem IBAN)
result = client.refunds.refund(
    transaction_id="29748010",
    amount=Decimal("3.45"),
    reason="Cliente cancelou",
)

assert result.status == PaymentStatus.REFUNDED
refund_id = result.raw_response["refundId"]  # ID do reembolso (audit)
```

## Multibanco exige IBAN **e** BIC

Multibanco liquida banco-a-banco, logo o reembolso precisa de saber para
que conta devolver o dinheiro. **`iban` e `bic` são ambos obrigatórios**
apesar de a documentação sugerir que `bic` é opcional — sem ele a eupago
devolve `BIC_INVALID` (provado definitivamente em produção a 2026-05-31:
`bic` ausente, `""` e `null` todos rejeitados; só uma string não vazia
é aceite):

```python
from eupago.utils import bic_for_pt_iban

iban_cliente = "PT50000201231234567890154"
client.refunds.refund(
    transaction_id="113068862",
    amount=Decimal("40.00"),
    iban=iban_cliente,
    bic=bic_for_pt_iban(iban_cliente),  # helper do SDK para os principais bancos PT
)
```

`bic_for_pt_iban` cobre os principais bancos de retalho em Portugal
(~99% das contas). Devolve `None` para bancos menores — nesse caso
pergunta ao cliente.

## Liquidação é assíncrona (e podes consultar)

Refunds Multibanco vêm com `status: "Pendente"` na resposta síncrona
(MB WAY / Cartão dão o `"Reembolsado"` imediato). O webhook de liquidação
chega depois — minutos a horas. Usa `WebhookEvent.original_transaction_id`
para reconciliar.

Se preferires consultar em vez de esperar pelo webhook:

```python
estado = client.refunds.get(refund_id)
# {"identifier": "ORD-...", "reference": "...", "status": "pendente"}
# muda para "Reembolsado" após liquidação
```

MB WAY e Cartão liquidam wallet-/cartão-a-cartão e não precisam de IBAN/BIC.

## Reembolso parcial

```python
parcial = client.refunds.refund(
    transaction_id="29748010",
    amount=Decimal("1.00"),  # menos que o total
    reason="Devolução parcial — 1 item de 3",
)
```

## Parâmetros

| Parâmetro        | Tipo      | Obrigatório | Descrição |
|------------------|-----------|-------------|-----------|
| `transaction_id` | `str`     | Sim         | ID da transação original (da resposta ou do webhook) |
| `amount`         | `Decimal` | Sim         | Valor a reembolsar (≤ valor original) |
| `reason`         | `str`     | Não         | Texto livre, fica no histórico |
| `iban`           | `str`     | Sim para Multibanco | Conta do cliente para reembolso banco-a-banco |
| `bic`            | `str`     | Não         | Código de routing; raramente necessário |

## Async

```python
async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
    result = await c.refunds.refund_async(
        transaction_id="29748010",
        amount=Decimal("3.45"),
    )
```

## Atalho de teste — injectar Bearer do backoffice

O login do backoffice (`/api/auth/login`) devolve um Bearer que funciona
nos mesmos endpoints `/api/management/*`, com os mesmos shapes. Enquanto
esperas pelas credenciais OAuth do suporte, podes correr reembolsos a
partir de um test/script com esse bearer:

```python
client = EupagoClient(
    api_key="...",
    management_bearer="<bearer de /api/auth/login>",
    sandbox=True,
)
client.refunds.refund(transaction_id="...", amount=Decimal("..."))
```

Isto bypass OAuth completamente. Em produção, prefere
`client_id`/`client_secret`.
