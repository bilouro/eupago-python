# Google Pay

## O que é

Pagamento via Google Pay. O SDK do eupago suporta-o de duas formas:

- **Fluxo hospedado (recomendado para web):** chamas `create_payment` e
  rediriges o browser do cliente para o `payment_url` que o eupago
  devolve. É o eupago que serve a Google Pay sheet, faz o handshake com
  a wallet e notifica-te por webhook. **Não precisas de merchant id do
  Google Pay** — o merchant é o eupago.
- **Fluxo nativo (apps mobile ou web com merchant id próprio):**
  obténs um token `PaymentData` via Google Pay JS API ou Android SDK e
  passa-lo ao `create_payment`. O eupago desencripta server-side e cobra
  o cartão directamente — sem redirect.

O fluxo hospedado é a escolha correcta para quase todas as web apps.
Usa o nativo só quando precisas da sheet inline (sem redirect) ou já
tens merchant id próprio no Google Pay.

## Fluxo hospedado — exemplo

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# Sem google_pay_token — fluxo hospedado.
payment = client.google_pay.create_payment(
    order_id="ORD-GP-001",
    amount=Decimal("39.90"),
    success_url="https://loja.exemplo/checkout/ok",
    error_url="https://loja.exemplo/checkout/fail",
)

# Redirige o browser para:
return redirect(payment.payment_url)
```

O estado final chega por webhook (ver [Webhooks](../webhooks/index.md)):

```python
event = client.webhooks.parse(body=request.body, headers=request.headers)
if event.status == PaymentStatus.PAID:
    confirmar_encomenda(event.order_id)
```

## Activação no backoffice eupago

Sandbox: pede ao suporte do eupago para activar Google Pay no canal demo
(ainda não é self-service). Produção: requer formulário de adesão
separado aprovado pelo compliance do eupago — ver
[o artigo Apple Pay / Google Pay do eupago](https://customer.support.eupago.com/servicedesk/customer/portal/2/article/1953857539).

## Fluxo nativo — avançado

Quando queres a Google Pay sheet inline (sem redirect), conduzes o
Google Pay no cliente e encaminhas o token resultante para o SDK:

```python
# Capturado do PaymentsClient.loadPaymentData no browser, ou da API
# Google Pay Android. O SDK trata o token como string opaca.
google_pay_token = '{"paymentMethodData": {"tokenizationData": {"token": "..."}}}'

payment = client.google_pay.create_payment(
    order_id="ORD-GP-002",
    amount=Decimal("39.90"),
    google_pay_token=google_pay_token,
)
```

Este caminho requer:

- Merchant configurado no Google Pay & Wallet Console.
- Dispositivo real com Google Pay activo para verificação live.

## Reembolso

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    amount=Decimal("39.90"),
)
```

Ver [Reembolsos](refund.md) para a configuração OAuth.

## Notas

- Quando omites `google_pay_token`, o SDK não envia `googlePayToken` no
  request — é assim que o eupago sabe que deve servir a sheet hospedada.
- O shape do corpo segue o contrato v1.02 do cartão de crédito.
- Vê o script runnable
  [`10_google_pay.py`](https://github.com/bilouro/eupago-python/blob/main/examples/10_google_pay.py).
