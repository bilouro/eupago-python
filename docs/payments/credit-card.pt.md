# Cartão de Crédito

## O que é

Pagamento de cartão de crédito/débito alojado com 3D-Secure / OTP. O cliente
é redirecionado para a página da eupago para introduzir os dados do cartão
e (se o cartão ou o valor o exigirem) completar o desafio 3DS. O resultado
chega por webhook.

O mesmo serviço cobre três fluxos:

- **`create_payment`** — cobrança imediata.
- **`authorize` + `capture`** — reservar agora, cobrar depois.
- **`create_subscription` + `charge_subscription`** — registar o cartão
  uma única vez e cobrar do servidor a qualquer momento.

O valor máximo por transação é **3.999 EUR**.

## Fluxo

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Cliente
    App->>eupago: create_payment(amount, success_url, error_url, back_url)
    eupago-->>App: redirectUrl + transactionID (status PENDING)
    App->>Cliente: Redirect para redirectUrl
    Cliente->>eupago: Introduz cartão + (opcional) OTP 3DS
    eupago->>App: Webhook (PAID / DECLINED)
```

## Exemplo — pagamento único

```python
from decimal import Decimal
from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="...", sandbox=True)

payment = client.credit_card.create_payment(
    order_id="ORD-CC-001",
    amount=Decimal("249.90"),
    success_url="https://loja.exemplo.pt/ok",
    error_url="https://loja.exemplo.pt/falha",
    back_url="https://loja.exemplo.pt/carrinho",
    customer=Customer(email="cliente@exemplo.pt"),
)

# Redirecciona o cliente para payment.payment_url e aguarda o webhook
```

**Cartão de teste (sandbox):** `4018810000150015` (Visa) — OTP `0101`
sucesso, `3333` falha. Valores acima de 500 EUR despoletam o OTP.

## Exemplo — authorize + capture

```python
auth = client.credit_card.authorize(
    order_id="ORD-CC-AUTH-001",
    amount=Decimal("100.00"),
    success_url="...", error_url="...", back_url="...",
)

# Mais tarde, quando o serviço for prestado — capture exige amount e as
# mesmas URLs (eupago rejeita corpo vazio com AMOUNT_MISSING).
captured = client.credit_card.capture(
    transaction_id=auth.transaction_id,
    amount=Decimal("100.00"),
    success_url="...", error_url="...", back_url="...",
)
```

!!! warning "Capacidade do canal"
    `authorize` + `capture` exigem que o canal eupago tenha **Cartão de
    Crédito — Auth & Capture** provisionado (uma feature separada do
    Cartão de Crédito básico). Num canal demo o formulário redirecciona
    para o `errorUrl` e o capture devolve `PAYMENT_NOT_CAPTIVE`. Pede ao
    suporte da eupago para activar a feature no teu canal.

## Exemplo — subscrição

```python
sub = client.credit_card.create_subscription(
    order_id="SUB-2026-001",
    amount=Decimal("19.90"),         # valor recorrente
    success_url="...", error_url="...", back_url="...",
    # Opcionais — defaults equivalem a mensalmente, dia 1, 1 ano:
    # periodicity="Mensal",
    # collection_day=1,
    # auto_process=False,            # True = eupago cobra automaticamente
    # start_date=date(2026, 6, 1),
    # limit_date=date(2027, 6, 1),
)

# sub.transaction_id é o subscriptionID (hex de 32 chars) — guarda-o.
subscription_id = sub.transaction_id

# Cobra depois (server-to-server, sem intervenção do cliente):
client.credit_card.charge_subscription(
    recurrent_id=subscription_id,
    order_id="SUB-2026-001-M01",
    amount=Decimal("19.90"),
    success_url="...", error_url="...", back_url="...",
)
```

!!! warning "Capacidade do canal"
    Endpoints de subscrição exigem que o canal tenha **Cartão de Crédito
    — Subscrição** provisionado pela eupago. Sem isso, o formulário de
    registo redirecciona para o `errorUrl` e qualquer
    `charge_subscription` é recusado. O SDK envia o body correcto
    (verificado contra a spec readme.io); activa a feature no
    backoffice ou via suporte.

## Reembolso

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    value=Decimal("249.90"),
)
```

Ver [Refunds](refund.md) para a configuração OAuth.

## Notas

- As três URLs de retorno (`success_url`, `error_url`, `back_url`) são
  exigidas pelo API em `create_payment`, `authorize` e
  `create_subscription`.
- As subscrições guardam o token do cartão do lado da eupago; cobranças
  subsequentes não requerem intervenção do cliente.
- Vê os scripts runnable
  [`07_credit_card_payment.py`](https://github.com/bilouro/eupago-python/blob/main/examples/07_credit_card_payment.py)
  e
  [`08_credit_card_subscription.py`](https://github.com/bilouro/eupago-python/blob/main/examples/08_credit_card_subscription.py)
  para o ciclo completo.
