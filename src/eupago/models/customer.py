from __future__ import annotations

from eupago.models._base import BaseModel


class Customer(BaseModel):
    name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    notify: bool = True
