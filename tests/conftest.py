from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_data() -> dict[str, Any]:
    cache: dict[str, Any] = {}

    def _load(name: str) -> dict[str, Any]:
        if name not in cache:
            path = FIXTURES_DIR / f"{name}.json"
            cache[name] = json.loads(path.read_text())
        return cache[name]

    return _load  # type: ignore[return-value]
