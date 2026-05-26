# Contributing

## Setup

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

## Running checks

```bash
ruff check .          # lint
ruff format .         # format
mypy src/             # type check
pytest                # tests (coverage enforced ≥85%)
```

## Pull requests

- One feature or fix per PR
- Include tests for new code
- Update CHANGELOG.md under `[Unreleased]`
- All CI checks must pass (lint, types, tests across Python 3.9–3.13)

## Reporting security issues

See [SECURITY.md](SECURITY.md) — do not open a public issue for vulnerabilities.
