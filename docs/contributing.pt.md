# Contribuir

Obrigado pelo interesse em contribuir para o eupago Python SDK!

## Setup em 3 comandos

```bash
git clone https://github.com/bilouro/eupago-python.git && cd eupago-python
pip install -e ".[dev]"
pre-commit install
```

Isto instala o SDK em modo editavel com todas as dependencias de desenvolvimento (ruff, mypy, pytest, pre-commit).

## Correr checks

Todos os checks devem passar antes de cada commit:

=== "Todos"

    ```bash
    ruff check .          # lint
    ruff format .         # auto-format
    mypy src/             # type check (--strict)
    pytest                # testes com coverage (≥85% enforced)
    ```

=== "Lint"

    ```bash
    ruff check .
    ruff check . --fix    # corrigir automaticamente
    ```

=== "Format"

    ```bash
    ruff format .                # formatar
    ruff format --check .        # verificar sem alterar
    ```

=== "Types"

    ```bash
    mypy src/                    # strict mode
    ```

=== "Testes"

    ```bash
    pytest                       # todos os testes
    pytest tests/unit/           # so unit tests
    pytest -k "test_create"      # por nome
    pytest -m "not integration"  # excluir integration tests
    ```

## Como adicionar um novo metodo de pagamento

O SDK segue um padrao consistente para cada metodo de pagamento:

1. Criar o ficheiro do servico em `src/eupago/services/`
2. Seguir o `mbway.py` como implementacao de referencia
3. Registar no client (`_client.py`)
4. Adicionar testes em `tests/unit/`
5. Actualizar `services/__init__.py`

Cada servico normaliza os nomes da API eupago (que diferem entre geracoes de endpoint) num unico vocabulario ingles — segue os servicos existentes para manter consistencia.

## Pull Requests

- **Um feature ou fix por PR** — nao mistures funcionalidades diferentes
- **Inclui testes** para codigo novo — coverage minimo de 85%
- **Actualiza o CHANGELOG.md** na seccao `[Unreleased]`
- **Todos os checks CI devem passar** — lint, types, testes (Python 3.9-3.13)
- Descreve o que mudou e porque no PR body

### Workflow tipico

```bash
# 1. Cria um branch
git checkout -b feature/payshop-service

# 2. Desenvolve e testa
pytest tests/unit/test_payshop.py

# 3. Verifica tudo
ruff check . && ruff format --check . && mypy src/ && pytest

# 4. Commit e push
git add .
git commit -m "Add Payshop payment service"
git push -u origin feature/payshop-service

# 5. Abre PR no GitHub
```

## Convencoes de codigo

- **Python ≥3.9** — usa `from __future__ import annotations`, nunca `match/case`
- **Decimal para dinheiro** — nunca `float`
- **Type annotations** em todas as funcoes publicas
- **Docstrings Google style**
- **`_filename.py`** = modulo interno, **`filename.py`** = API publica
- **Nao logar PII** — telefones, emails, NIF sao redactados automaticamente

## Seguranca

Para reportar vulnerabilidades de seguranca, consulta o [SECURITY.md](https://github.com/bilouro/eupago-python/blob/main/SECURITY.md).

!!! danger "Nao abras issue publico"
    Vulnerabilidades de seguranca devem ser reportadas por email privado, nunca num issue publico do GitHub.
