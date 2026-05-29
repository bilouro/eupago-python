# eupago Python SDK

[![PyPI version](https://img.shields.io/pypi/v/eupago)](https://pypi.org/project/eupago/)
[![Python versions](https://img.shields.io/pypi/pyversions/eupago)](https://pypi.org/project/eupago/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/bilouro/eupago-python/blob/main/LICENSE)

O primeiro SDK Python para a [eupago](https://www.eupago.com), o gateway de pagamentos português.

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
| **MB WAY** | Pagamento via telemóvel (aprovação em 5 min) | `client.mbway` |
| **Multibanco** | Referência para ATM ou homebanking | `client.multibanco` |

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
