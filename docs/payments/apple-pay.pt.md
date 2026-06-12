# Apple Pay

## O que é

Pagamento via Apple Wallet. O SDK do eupago suporta-o de duas formas:

- **Fluxo hospedado (recomendado para web):** chamas `create_payment` e
  rediriges o browser do cliente para o `payment_url` que o eupago
  devolve. É o eupago que serve a Apple Pay sheet, faz o handshake com
  a wallet e notifica-te por webhook. **Não precisas de conta Apple
  Developer** — o merchant é o eupago.
- **Fluxo nativo (apps mobile ou web com Merchant ID próprio):**
  obténs um `PKPaymentToken` via Apple Pay JS API ou iOS SDK e passa-lo
  ao `create_payment`. O eupago desencripta server-side e cobra o
  cartão directamente — sem redirect.

O fluxo hospedado é a escolha correcta para quase todas as web apps.
Usa o nativo só quando precisas da sheet inline (sem redirect) ou já
tens Apple Pay Merchant ID próprio.

## Fluxo hospedado — exemplo

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# Sem apple_pay_token — fluxo hospedado.
payment = client.apple_pay.create_payment(
    order_id="ORD-AP-001",
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

Sandbox: pede ao suporte do eupago para activar Apple Pay no canal demo
(ainda não é self-service). Produção: requer formulário de adesão
separado aprovado pelo compliance do eupago — ver
[o artigo Apple Pay / Google Pay do eupago](https://customer.support.eupago.com/servicedesk/customer/portal/2/article/1953857539).

!!! warning "Limitação do sandbox (a 2026-06-12)"
    Em `sandbox.eupago.pt` a Apple Pay sheet alojada abre e fecha-se
    de imediato: o endpoint de merchant validation do eupago
    (`POST /api/extern/applepay/merchant/{id}`) devolve
    `400 BAD_REQUEST`, e a página aborta a `ApplePaySession` antes
    de qualquer autenticação na wallet. O `create_payment` →
    `redirectUrl` funciona; só o handshake da sheet está partido,
    server-side. Reportado ao eupago. Nenhum cartão é cobrado — a
    sessão morre antes do Touch ID / Face ID.

## Fluxo nativo — avançado

Quando queres a Apple Pay sheet inline (sem redirect), conduzes o Apple
Pay no cliente e encaminhas o token resultante para o SDK:

```python
# Capturado do window.ApplePaySession no browser, ou do PassKit delegate
# no iOS. O SDK trata o token como string opaca.
apple_pay_token = '{"paymentMethod": "...", "paymentData": {"version": "EC_v1", ...}}'

payment = client.apple_pay.create_payment(
    order_id="ORD-AP-002",
    amount=Decimal("39.90"),
    apple_pay_token=apple_pay_token,
)
```

Este caminho requer:

- Conta Apple Developer com Apple Pay Merchant ID.
- Verificação de domínio do fluxo Apple Pay do eupago.
- Dispositivo real com Wallet activa para verificação live.

## Reembolso

```python
client.refunds.refund(
    transaction_id=payment.transaction_id,
    amount=Decimal("39.90"),
)
```

Ver [Reembolsos](refund.md) para a configuração OAuth.

## Notas

- Quando omites `apple_pay_token`, o SDK não envia `applePayToken` no
  request — é assim que o eupago sabe que deve servir a sheet hospedada.
- O shape do corpo segue o contrato v1.02 do cartão de crédito.
- Vê o script runnable
  [`09_apple_pay.py`](https://github.com/bilouro/eupago-python/blob/main/examples/09_apple_pay.py).
