# Configuration

## Client options

```python
from eupago import EupagoClient

client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",  # Required
    sandbox=True,           # Sandbox environment (default: False)
    timeout=10.0,           # Timeout in seconds (default: 10)
    max_retries=3,          # Retries on failed GETs (default: 3)
    client_id="...",        # OAuth — for management endpoints (optional)
    client_secret="...",    # OAuth — for management endpoints (optional)
)
```

## Sandbox vs Production

| | Sandbox | Production |
|---|---|---|
| URL | `sandbox.eupago.pt` | `clientes.eupago.pt` |
| Parameter | `sandbox=True` | `sandbox=False` (default) |
| API Key | Test key | Production key |
| Payments | Simulated | Real |

!!! tip "Always use sandbox for development"
    Never use production API keys during development. Request sandbox credentials from eupago support: suporte@eupago.pt

## Retries

The SDK automatically retries with exponential backoff + jitter, but **only on GET requests** (status queries).

**POST requests never retry** — eupago doesn't support idempotency keys, and retrying a POST can create duplicate payments.

## Audit hook

Log every API call for debugging, metrics, or auditing:

```python
def log_api_call(request, response, duration_ms):
    print(f"{request.method} {request.url} → {response.status_code} ({duration_ms:.0f}ms)")

client.set_audit_hook(log_api_call)
```

## OAuth (management endpoints)

For refunds, transaction queries, and payouts, eupago requires OAuth 2.0:

```python
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
```

The SDK manages the token automatically — fetches, caches, and refreshes on expiry.

## Context manager

The client supports `with` (sync) and `async with` for connection cleanup:

```python
# Sync
with EupagoClient(api_key="...") as client:
    payment = client.mbway.create_payment(...)

# Async
async with EupagoClient(api_key="...") as client:
    payment = await client.mbway.create_payment_async(...)
```
