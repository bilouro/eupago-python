from __future__ import annotations

import logging
import re

logger = logging.getLogger("eupago")

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{9}\b"), "***PHONE***"),
    (re.compile(r"\b351#\d{9}\b"), "***PHONE***"),
    (re.compile(r"\b[+]351\s?\d{9}\b"), "***PHONE***"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "***EMAIL***"),
    (re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}\b"), "***NIF***"),
]


def redact_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class PiiFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_pii(record.msg)
        return True


logger.addFilter(PiiFilter())
