"""MB WAY payment — minimal example."""

from decimal import Decimal

from eupago import EupagoClient

client = EupagoClient(
    api_key="your-api-key-here",
    sandbox=True,
)

payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="351#912345678",
)

print(f"Transaction: {payment.transaction_id}")
print(f"Status: {payment.status}")
print(f"Amount: {payment.amount} {payment.currency}")
