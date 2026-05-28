"""MkDocs build hooks."""

from __future__ import annotations

import logging
from typing import Any


def on_config(config: Any, **kwargs: Any) -> Any:
    # The i18n plugin renders every mkdocstrings symbol once per locale
    # (e.g. /api/ and /en/api/), so mkdocs-autorefs reports each as having
    # "Multiple primary URLs". That is expected for a bilingual site and not
    # actionable, but it would otherwise abort `mkdocs build --strict`.
    # Silence only that logger; every other warning still fails strict mode.
    logging.getLogger("mkdocs.plugins.mkdocs_autorefs").setLevel(logging.ERROR)
    return config
