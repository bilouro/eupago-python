"""Sandbox backoffice automation helper for SDK integration tests.

Lets the integration test programmatically trigger "Marcar como Paga" on a
Multibanco reference so the SDK can capture a real "Paid" webhook without
manual clicks in the backoffice UI.

**Sandbox-only and brittle:** this scrapes the eupago backoffice (an UI, not
a public API) — any change to that UI may break it. Reverse-engineered from
the network calls the browser makes.

Auth flow::

    POST /clientes/auth/connectbo   {user, password}     -> JWT (Authorization)
                                                            + PHPSESSID cookie
    POST /api/auth/login            {username, password} -> Bearer token
    GET  /clientes/auth/myuser      (with JWT)           -> activates the PHP
    GET  /clientes/contas/services  (with JWT)              session for the
                                                            /clientes/pagamentos/
                                                            endpoints (without
                                                            these two, como_paga
                                                            is silently dropped)

Used afterwards::

    POST /api/intern/v1.02/references?identifier=...     -> rows w/ DT_RowId (refid)
         Headers: Authorization: Bearer <token>,
                  x-auth-token: base64("Auth-Token-Eupago-YYYYMMDD")
    POST /clientes/pagamentos/como_paga_demo_por_soap    -> mark paid
         Body:    refid=<id>&_mcasgrifc=sid:<sha1(PHPSESSID+ts)>,<ts>
         Headers: Authorization: <JWT>

Credentials come from ``EUPAGO_BACKOFFICE_EMAIL`` / ``EUPAGO_BACKOFFICE_PASSWORD``.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import sys
import time
from typing import Any

import httpx

_SANDBOX_BASE = "https://sandbox.eupago.pt"
_PRODUCTION_BASE = "https://clientes.eupago.pt"
# Backwards-compat alias used by older call sites.
_BASE = _SANDBOX_BASE


class BackofficeError(RuntimeError):
    """Backoffice helper failure (HTTP error, not-found, etc.)."""


class BackofficeSession:
    def __init__(
        self,
        email: str,
        password: str,
        *,
        production: bool = False,
    ) -> None:
        self._email = email
        self._password = password
        self._base = _PRODUCTION_BASE if production else _SANDBOX_BASE
        self._client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        self._jwt: str | None = None
        self._bearer: str | None = None

    def __enter__(self) -> BackofficeSession:
        self.login()
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def login(self) -> None:
        body = json.dumps({"user": self._email, "password": self._password})
        r = self._client.post(
            f"{self._base}/clientes/auth/connectbo",
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded, application/json",
                "Accept": "application/json",
            },
        )
        r.raise_for_status()
        self._jwt = r.json()["access_token"]

        r = self._client.post(
            f"{self._base}/api/auth/login",
            data={"username": self._email, "password": self._password},
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        self._bearer = r.json()["authorisation"]

        # Bootstrap calls that the browser fires after login — these load the
        # user profile + channel services into the PHP session and are required
        # for the /clientes/pagamentos/ endpoints to accept us.
        self._client.get(
            f"{self._base}/clientes/auth/myuser", headers={"Authorization": self._jwt}
        ).raise_for_status()
        self._client.get(
            f"{self._base}/clientes/contas/services", headers={"Authorization": self._jwt}
        ).raise_for_status()

    def _x_auth_token(self) -> str:
        today = dt.date.today().strftime("%Y%m%d")
        return base64.b64encode(f"Auth-Token-Eupago-{today}".encode()).decode()

    def find_row(
        self,
        *,
        identifier: str | None = None,
        reference: str | None = None,
        date: dt.date | None = None,
    ) -> dict[str, Any]:
        """Look up a transaction by identifier (preferred) or reference.

        Returns the DataTables row dict containing ``DT_RowId`` (the refid).
        """
        if not (identifier or reference):
            raise ValueError("identifier or reference is required")
        when = date or dt.date.today()
        params = {
            "status": "",
            "start_date": when.isoformat(),
            "end_date": when.isoformat(),
            "value": "",
            "identifier": identifier or "",
            "service": "",
            "channel": "",
        }
        data = {
            "draw": "1",
            "start": "0",
            "length": "25",
            "search[value]": identifier or reference or "",
            "search[regex]": "false",
        }
        r = self._client.post(
            f"{self._base}/api/intern/v1.02/references",
            params=params,
            data=data,
            headers={
                "Authorization": f"Bearer {self._bearer}",
                "x-auth-token": self._x_auth_token(),
                "Accept": "application/json",
                "Origin": self._base,
            },
        )
        r.raise_for_status()
        rows: list[dict[str, Any]] = r.json().get("data", [])
        if identifier:
            rows = [row for row in rows if row.get("identificador") == identifier]
        if reference:
            rows = [row for row in rows if str(row.get("referencia")) == str(reference)]
        if not rows:
            raise BackofficeError(
                f"No reference found (identifier={identifier!r}, reference={reference!r})"
            )
        return rows[0]

    def mark_paid(self, refid: str) -> dict[str, Any]:
        # /api/auth/login sets its own PHPSESSID on /api/; we need the /clientes/ one.
        phpsess = self._client.cookies.get("PHPSESSID", path="/clientes/")
        if not phpsess:
            raise BackofficeError("No PHPSESSID — call login() first")
        ts = int(time.time())
        sha = hashlib.sha1((phpsess + str(ts)).encode()).hexdigest()  # noqa: S324 (vendor scheme)
        mcas = f"sid:{sha},{ts}"
        r = self._client.post(
            f"{self._base}/clientes/pagamentos/como_paga_demo_por_soap",
            data={"refid": str(refid), "_mcasgrifc": mcas},
            headers={
                "Authorization": self._jwt or "",
                "Content-Type": "application/x-www-form-urlencoded, application/json",
                "Accept": "application/json",
                "Origin": self._base,
            },
        )
        r.raise_for_status()
        result: dict[str, Any] = r.json()
        if result.get("tipo") != "sucesso":
            raise BackofficeError(f"mark_paid did not succeed: {result}")
        return result

    def mark_paid_by_identifier(self, identifier: str) -> dict[str, Any]:
        return self.mark_paid(self.find_row(identifier=identifier)["DT_RowId"])


def _main() -> int:
    p = argparse.ArgumentParser(description="Mark a sandbox Multibanco reference as Paga.")
    p.add_argument("--identifier", help="payment identifier (e.g. SDK order_id)")
    p.add_argument("--reference", help="Multibanco reference number")
    args = p.parse_args()
    try:
        email = os.environ["EUPAGO_BACKOFFICE_EMAIL"]
        password = os.environ["EUPAGO_BACKOFFICE_PASSWORD"]
    except KeyError as exc:
        print(f"missing env var: {exc}", file=sys.stderr)
        return 2
    with BackofficeSession(email, password) as s:
        row = s.find_row(identifier=args.identifier, reference=args.reference)
        print(
            f"found refid={row['DT_RowId']} ref={row['referencia']} "
            f"ident={row['identificador']} estado={row['estado']}"
        )
        if row["estado"] == "paga":
            print("already paid, nothing to do")
            return 0
        result = s.mark_paid(row["DT_RowId"])
        print(f"mark_paid -> {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
