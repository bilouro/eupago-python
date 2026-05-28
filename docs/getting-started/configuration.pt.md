# Configuração

## Opções do client

```python
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",  # Obrigatório
    sandbox=True,           # Ambiente sandbox (default: False)
    timeout=10.0,           # Timeout em segundos (default: 10)
    max_retries=3,          # Retries em GETs falhados (default: 3)
    client_id="...",        # OAuth — para endpoints de gestão (opcional)
    client_secret="...",    # OAuth — para endpoints de gestão (opcional)
)
```

## Sandbox vs Produção

| | Sandbox | Produção |
|---|---|---|
| URL | `sandbox.eupago.pt` | `clientes.eupago.pt` |
| Parâmetro | `sandbox=True` | `sandbox=False` (default) |
| API Key | Key de teste | Key de produção |
| Pagamentos | Simulados | Reais |

!!! tip "Usa sempre sandbox para desenvolvimento"
    Nunca uses a API key de produção em desenvolvimento. Pede credenciais de sandbox ao suporte eupago: suporte@eupago.pt

## Retries

O SDK faz retry automático com exponential backoff + jitter, mas **apenas em requests GET** (consultas de estado).

Requests **POST nunca fazem retry** — a eupago não suporta idempotency keys, e repetir um POST pode criar pagamentos duplicados.

## Audit hook

Regista cada chamada à API para logging, métricas ou debug:

```python
def log_api_call(request, response, duration_ms):
    print(f"{request.method} {request.url} → {response.status_code} ({duration_ms:.0f}ms)")

client.set_audit_hook(log_api_call)
```

## OAuth (endpoints de gestão)

Para refunds, consulta de transações e payouts, a eupago requer OAuth 2.0:

```python
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    client_id="o-teu-client-id",
    client_secret="o-teu-client-secret",
)
```

O SDK gere o token automaticamente — pede, guarda em cache, e renova quando expira.

## Context manager

O client suporta `with` (sync) e `async with` para limpar conexões:

```python
# Sync
with EupagoClient(api_key="...") as client:
    payment = client.mbway.create_payment(...)

# Async
async with EupagoClient(api_key="...") as client:
    payment = await client.mbway.create_payment_async(...)
```
