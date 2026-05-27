# Contributing

Thank you for your interest in contributing to the eupago Python SDK!

## Setup in 3 commands

```bash
git clone https://github.com/bilouro/eupago-python.git && cd eupago-python
pip install -e ".[dev]"
pre-commit install
```

This installs the SDK in editable mode with all development dependencies (ruff, mypy, pytest, pre-commit).

## Running checks

All checks must pass before each commit:

=== "All"

    ```bash
    ruff check .          # lint
    ruff format .         # auto-format
    mypy src/             # type check (--strict)
    pytest                # tests with coverage (≥85% enforced)
    ```

=== "Lint"

    ```bash
    ruff check .
    ruff check . --fix    # auto-fix
    ```

=== "Format"

    ```bash
    ruff format .                # format
    ruff format --check .        # check without modifying
    ```

=== "Types"

    ```bash
    mypy src/                    # strict mode
    ```

=== "Tests"

    ```bash
    pytest                       # all tests
    pytest tests/unit/           # unit tests only
    pytest -k "test_create"      # by name
    pytest -m "not integration"  # exclude integration tests
    ```

## How to add a new payment method

The SDK follows a consistent pattern for each payment method. Refer to the `CLAUDE.md` file at the project root for detailed instructions, including:

1. Create the service file in `src/eupago/services/`
2. Follow `mbway.py` as the reference implementation
3. Register in the client (`_client.py`)
4. Add tests in `tests/unit/`
5. Update `services/__init__.py`

`CLAUDE.md` also contains the unified vocabulary table (SDK field names vs eupago API names) and all development rules.

## Pull Requests

- **One feature or fix per PR** — do not mix different functionalities
- **Include tests** for new code — minimum 85% coverage
- **Update CHANGELOG.md** under the `[Unreleased]` section
- **All CI checks must pass** — lint, types, tests (Python 3.9-3.13)
- Describe what changed and why in the PR body

### Typical workflow

```bash
# 1. Create a branch
git checkout -b feature/payshop-service

# 2. Develop and test
pytest tests/unit/test_payshop.py

# 3. Verify everything
ruff check . && ruff format --check . && mypy src/ && pytest

# 4. Commit and push
git add .
git commit -m "Add Payshop payment service"
git push -u origin feature/payshop-service

# 5. Open PR on GitHub
```

## Code conventions

- **Python >=3.9** — use `from __future__ import annotations`, never `match/case`
- **Decimal for money** — never `float`
- **Type annotations** on all public functions
- **Google style docstrings**
- **`_filename.py`** = internal module, **`filename.py`** = public API
- **No PII in logs** — phone numbers, emails, NIF are automatically redacted

## Security

To report security vulnerabilities, see [SECURITY.md](https://github.com/bilouro/eupago-python/blob/main/SECURITY.md).

!!! danger "Do not open a public issue"
    Security vulnerabilities must be reported via private email, never in a public GitHub issue.
