# Reembolsos

## O que são

Reverter uma transação previamente paga — total ou parcialmente. Funciona
para qualquer método (MB WAY, Multibanco, Cartão, Apple/Google Pay,
Pay By Link, …).

Os reembolsos usam a **API de management** do eupago, que tem autenticação
distinta dos restantes endpoints.

## ⚠️ Sem webhook em reembolsos

Ao contrário dos pagamentos, **o eupago NÃO emite webhook para reembolsos**.
Trata a resposta síncrona como fonte de verdade:

```python
if result.status == PaymentStatus.REFUNDED:
    ...
```

Se precisares de uma segunda fonte, consulta o endpoint de transações da
API de management após o reembolso.

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

# Reembolso total
result = client.refunds.refund(
    transaction_id="113068862",
    value=Decimal("64.00"),
    reason="Cliente cancelou",
)

assert result.status == PaymentStatus.REFUNDED
```

## Reembolso parcial

```python
parcial = client.refunds.refund(
    transaction_id="113068862",
    value=Decimal("20.00"),  # menos que o total
    reason="Devolução parcial — 1 item de 3",
)
```

## Parâmetros

| Parâmetro        | Tipo      | Obrigatório | Descrição |
|------------------|-----------|-------------|-----------|
| `transaction_id` | `str`     | Sim         | ID da transação original (da resposta do pagamento ou do webhook) |
| `value`          | `Decimal` | Sim         | Valor a reembolsar (≤ valor original) |
| `currency`       | `str`     | Não         | ISO 4217. Default `"EUR"` |
| `reason`         | `str`     | Não         | Texto livre, fica no histórico da transação |

## Async

```python
async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
    result = await c.refunds.refund_async(
        transaction_id="113068862",
        value=Decimal("64.00"),
    )
```
