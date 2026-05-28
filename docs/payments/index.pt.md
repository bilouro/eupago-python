# Qual método escolher?

## Guia de decisão

| Preciso de... | Método | Tempo de pagamento | Valor máx. |
|---|---|---|---|
| Pagamento imediato via telemóvel | [MB WAY](mbway.md) | 5 minutos | 99.999 EUR |
| Referência para ATM ou homebanking | [Multibanco](multibanco.md) | 1–30 dias | 99.999 EUR |

## Fluxos comparados

### Pagamento directo (MB WAY)

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Cliente
    App->>eupago: Criar pagamento
    eupago-->>App: transactionID
    eupago->>Cliente: Notificação
    Cliente->>eupago: Aprova
    eupago->>App: Webhook (PAID)
```

### Referência (Multibanco)

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Cliente
    App->>eupago: Criar referência
    eupago-->>App: entidade + referência
    App->>Cliente: Mostra entidade/referência
    Cliente->>ATM/Banco: Paga com a referência
    eupago->>App: Webhook (PAID)
```

## Todos os métodos usam o mesmo padrão

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# O resultado é sempre PaymentResult
result = client.{método}.create_payment(
    order_id="ORD-001",
    amount=Decimal("49.90"),
    ...
)

print(result.status)          # PaymentStatus.PENDING
print(result.transaction_id)  # ID da transação
print(result.raw_response)    # JSON original da eupago
```
