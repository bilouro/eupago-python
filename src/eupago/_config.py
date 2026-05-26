from __future__ import annotations

SANDBOX_BASE_URL = "https://sandbox.eupago.pt"
PRODUCTION_BASE_URL = "https://clientes.eupago.pt"

API_PREFIX = "/api/v1.02"
LEGACY_PREFIX = "/clientes/rest_api"
AUTH_PREFIX = "/api/auth"
MANAGEMENT_PREFIX = "/api/management/v1.02"

DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RETRIES = 3
MAX_RETRY_DELAY = 5.0
INITIAL_RETRY_DELAY = 0.5
