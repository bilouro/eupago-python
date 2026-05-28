"""
Async — Usar o SDK com async/await.

Todos os métodos têm variante _async. Ideal para FastAPI, aiohttp,
ou qualquer aplicação assíncrona.
"""

import asyncio
from decimal import Decimal

from eupago import EupagoClient


async def main() -> None:
    # Context manager fecha conexões automaticamente
    async with EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True) as client:

        # MB WAY async
        mbway = await client.mbway.create_payment_async(
            order_id="ASYNC-001",
            amount=Decimal("25.00"),
            phone_number="351#912345678",
        )
        print(f"MB WAY: {mbway.transaction_id}")

        # Multibanco async
        ref = await client.multibanco.create_reference_async(
            order_id="ASYNC-002",
            amount=Decimal("50.00"),
        )
        print(f"Multibanco: {ref.entity} / {ref.reference}")

        # Múltiplos pagamentos em paralelo
        results = await asyncio.gather(
            client.mbway.create_payment_async(
                order_id="PARALLEL-001",
                amount=Decimal("10.00"),
                phone_number="351#912345678",
            ),
            client.multibanco.create_reference_async(
                order_id="PARALLEL-002",
                amount=Decimal("20.00"),
            ),
        )
        for r in results:
            print(f"  {r.method}: {r.transaction_id or r.reference}")


asyncio.run(main())
