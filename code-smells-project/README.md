# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

`pytest` já roda com cobertura (`--cov`). Os testes usam um banco SQLite temporário por teste — nada é escrito em `loja.db`.

