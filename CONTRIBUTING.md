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

## Test discipline (please read)

Two layers, **both required** for new wire-touching code:

- **Unit** (`tests/unit/`) — mock httpx with `respx` and **assert the exact request body** sent on the wire, not just the return value. This is what catches wrong field names / shapes / required-but-missing fields. Coverage gate ≥85%.
- **Live** (`tests/integration/`) — exercise the operation against the real eupago sandbox (skipped automatically when env vars are missing). When the upstream channel doesn't have a feature provisioned, use `pytest.skip("clear reason …")` rather than letting the test pass silently.

For the README / CHANGELOG / roadmap, status is **per operation** (not per service). `service.create_payment` being live-validated does not entitle `service.authorize` to a green check. See the matrix style in `README.md` for the convention. The longer rationale lives in `CLAUDE.md` under **R12: Testing Discipline**.

## Reporting security issues

See [SECURITY.md](SECURITY.md) — do not open a public issue for vulnerabilities.
