# eupago Python SDK

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "eupago Python SDK",
  "alternateName": ["eupago-python", "SDK eupago para Python"],
  "applicationCategory": "DeveloperApplication",
  "applicationSubCategory": "Payment Gateway SDK",
  "operatingSystem": "Cross-platform",
  "programmingLanguage": "Python",
  "softwareVersion": "0.5.2",
  "license": "https://opensource.org/licenses/MIT",
  "url": "https://eupago.bilouro.com/pt/",
  "downloadUrl": "https://pypi.org/project/eupago/",
  "codeRepository": "https://github.com/bilouro/eupago-python",
  "description": "SDK Python moderno e totalmente tipado para a eupago (Portugal): MB WAY, Multibanco, Cartão de Crédito, Pay By Link, reembolsos e webhooks. Sync + async, validado em produção.",
  "inLanguage": "pt-PT",
  "author": {
    "@type": "Person",
    "name": "Victor Bilouro",
    "url": "https://github.com/bilouro"
  },
  "keywords": "eupago, Python, SDK, MB WAY, Multibanco, pagamentos, gateway de pagamento, Portugal, Pay By Link, reembolso, webhook"
}
</script>

[![PyPI version](https://img.shields.io/pypi/v/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago.svg?style=flat-square)](https://pypi.org/project/eupago/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://github.com/bilouro/eupago-python/blob/main/LICENSE)

O primeiro SDK Python para a [eupago](https://www.eupago.com), o gateway de pagamentos português. Aceita pagamentos **MB WAY**, **Multibanco**, **Cartão de Crédito** e **Pay By Link**, emite reembolsos e verifica webhooks — sync e async, totalmente tipado, validado em produção.

!!! warning "SDK da comunidade"
    Este é um projecto open-source independente, não afiliado nem endossado pela eupago.

## Quickstart

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="a-tua-key", sandbox=True)

payment = client.mbway.create_payment(
    order_id="ORD-001",
    amount=Decimal("49.90"),
    phone_number="912345678",
)

print(payment.transaction_id)  # "txn-abc-123"
print(payment.status)          # PaymentStatus.PENDING
```

## Métodos de pagamento

| Método | Descrição | Módulo |
|---|---|---|
| **[MB WAY](payments/mbway.md)** | Pagamento via telemóvel com push notification (aprovação em 5 min) | `client.mbway` |
| **[Multibanco](payments/multibanco.md)** | Referência ATM / homebanking, paga em 1–30 dias | `client.multibanco` |
| **[Cartão de Crédito](payments/credit-card.md)** | Página alojada com 3D-Secure / OTP — suporta auth+capture e subscrições recorrentes | `client.credit_card` |
| **[Apple Pay](payments/apple-pay.md)** | Token Apple Wallet para apps iOS e Safari | `client.apple_pay` |
| **[Google Pay](payments/google-pay.md)** | Token Google Pay para apps Android e Chrome | `client.google_pay` |
| **[Pay By Link](payments/pay-by-link.md)** | Um único URL alojado — o cliente escolhe o método (MB WAY, Multibanco, Cartão, Apple/Google Pay, Cofidis…) | `client.pay_by_link` |
| **[Reembolsos](payments/refund.md)** | Reembolso total ou parcial de qualquer transação paga (OAuth) | `client.refunds` |

Webhooks (em claro **e** encriptados AES-256-CBC) e parsing v1.0 / v2.0 estão
cobertos por `client.webhooks.parse(...)` — ver [Webhooks](webhooks/index.md).

## Porquê este SDK?

- **Sync + Async** — mesmo client, suffix `_async` para métodos assíncronos
- **100% tipado** — `mypy --strict`, autocomplete total no IDE
- **Decimal** — nunca float para dinheiro
- **Bilingue** — documentação em Português e English
- **Webhooks** — parsing + verificação HMAC-SHA256
- **Retries seguros** — só em GETs, POST nunca repete (risco de pagamento duplicado)

## Próximos passos

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Instalação**

    ---

    Instalar e configurar em 2 minutos

    [:octicons-arrow-right-24: Começar](getting-started/index.md)

-   :material-credit-card:{ .lg .middle } **Pagamentos**

    ---

    Qual método usar? Guia de decisão

    [:octicons-arrow-right-24: Pagamentos](payments/index.md)

-   :material-webhook:{ .lg .middle } **Webhooks**

    ---

    Receber notificações de pagamento

    [:octicons-arrow-right-24: Webhooks](webhooks/index.md)

-   :material-flask:{ .lg .middle } **Receitas**

    ---

    Guias completos para FastAPI, Django, Flask

    [:octicons-arrow-right-24: Receitas](recipes/index.md)

</div>
