# Which method to choose?

## Decision guide

| I need to... | Method | Payment time | Max amount |
|---|---|---|---|
| Immediate mobile payment | [MB WAY](mbway.md) | 5 minutes | 99,999 EUR |
| ATM or online banking reference | [Multibanco](multibanco.md) | 1–30 days | 99,999 EUR |

## Compared flows

### Direct payment (MB WAY)

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Customer
    App->>eupago: Create payment
    eupago-->>App: transactionID
    eupago->>Customer: Notification
    Customer->>eupago: Approves
    eupago->>App: Webhook (PAID)
```

### Reference (Multibanco)

```mermaid
sequenceDiagram
    participant App
    participant eupago
    participant Customer
    App->>eupago: Create reference
    eupago-->>App: entity + reference
    App->>Customer: Show entity/reference
    Customer->>ATM/Bank: Pay with the reference
    eupago->>App: Webhook (PAID)
```

## All methods follow the same pattern

```python
from decimal import Decimal
from eupago import EupagoClient

client = EupagoClient(api_key="...", sandbox=True)

# The result is always PaymentResult
result = client.{method}.create_payment(
    order_id="ORD-001",
    amount=Decimal("49.90"),
    ...
)

print(result.status)          # PaymentStatus.PENDING
print(result.transaction_id)  # Transaction ID
print(result.raw_response)    # Raw eupago JSON
```
