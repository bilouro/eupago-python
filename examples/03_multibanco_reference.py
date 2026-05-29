"""
Multibanco — Gerar referência para pagamento em ATM ou homebanking.

O cliente recebe uma entidade + referência e paga quando quiser
(ATM, homebanking, app do banco). Pode demorar 1 a 30 dias.

Fluxo:
  App → create_reference → Mostra entidade/referência ao cliente
  → Cliente paga no ATM/banco → Webhook (PAID)
"""

from datetime import date
from decimal import Decimal

from eupago import EupagoClient

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Gerar referência simples
ref = client.multibanco.create_reference(
    order_id="ORD-2026-002",
    amount=Decimal("149.90"),
)

print(f"Entidade:   {ref.entity}")  # Ex: "11249"
print(f"Referência: {ref.reference}")  # Ex: "999888777"
print(f"Montante:   {ref.amount} EUR")

# Mostrar ao cliente:
# "Pague por Multibanco:
#  Entidade: 11249
#  Referência: 999 888 777
#  Montante: 149,90 EUR"


# --- Opções avançadas ---

# Com data de expiração + lembrete por email
ref_expiry = client.multibanco.create_reference(
    order_id="ORD-2026-003",
    amount=Decimal("75.00"),
    expires_at=date(2026, 6, 30),  # Expira a 30 de Junho
    starts_at=date(2026, 5, 27),  # Válida a partir de hoje
    send_expiry_reminder=True,  # Email de lembrete antes de expirar
    email="cliente@email.com",
)

# Permitir pagamentos duplicados (ex: donativos)
ref_dup = client.multibanco.create_reference(
    order_id="DONATIVO-001",
    amount=Decimal("10.00"),
    allow_duplicate=True,  # Mesmo referência pode ser paga várias vezes
)

# Referência com range de valores (cliente escolhe quanto pagar)
ref_range = client.multibanco.create_reference(
    order_id="CARREGAMENTO-001",
    amount=Decimal("50.00"),  # Valor sugerido
    min_amount=Decimal("10.00"),  # Mínimo 10 EUR
    max_amount=Decimal("100.00"),  # Máximo 100 EUR
)


# --- Consultar estado de uma referência ---

info = client.multibanco.get_info(
    reference="999888777",
    entity="11249",
)

print(f"Estado: {info.status}")  # PENDING ou PAID
print(f"Pedido: {info.order_id}")


# --- Reembolso (após pago) ---
#
# Quando a referência já foi paga, podes reembolsar via OAuth — ver
# examples/12_refund.py para a configuração completa.
#
# refund = client.refunds.refund(
#     transaction_id=info.transaction_id,
#     value=Decimal("149.90"),
# )
