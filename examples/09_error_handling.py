"""
Tratamento de erros — Como lidar com falhas.

Todas as excepções herdam de EupagoError.
Usa try/except com as classes específicas para tratar cada caso.
"""

from decimal import Decimal

from eupago import (
    AuthenticationError,
    EupagoClient,
    EupagoError,
    NetworkError,
    PaymentError,
    ValidationError,
)

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

try:
    payment = client.mbway.create_payment(
        order_id="ORD-ERR-001",
        amount=Decimal("49.90"),
        phone_number="351#912345678",
    )
    print(f"Sucesso: {payment.transaction_id}")

except ValidationError as e:
    # Erro de validação local (antes de chamar a API)
    # Ex: amount=0, phone_number vazio
    print(f"Dados inválidos: {e.message}")

except AuthenticationError as e:
    # API key inválida ou expirada
    # Solução: verificar key no backoffice eupago
    print(f"Autenticação falhou: {e.message}")

except PaymentError as e:
    # Pagamento recusado pela eupago
    print(f"Pagamento falhou: {e.message}")
    print(f"  HTTP status: {e.status_code}")
    print(f"  Código erro: {e.error_code}")

except NetworkError as e:
    # Timeout, sem conexão, DNS falhou
    # Solução: tentar novamente mais tarde
    print(f"Erro de rede: {e.message}")

except EupagoError as e:
    # Catch-all para qualquer erro do SDK
    print(f"Erro eupago: {e.message}")
