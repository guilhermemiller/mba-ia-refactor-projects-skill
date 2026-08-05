# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Diferente dos outros projetos, este já possui alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`), mas ainda contém problemas arquiteturais e de qualidade.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

`pytest` já roda com cobertura (`--cov`). Os testes de models, routes, services e helpers usam SQLite em memória; os smoke tests de `app.py`/`seed.py` criam e apagam `instance/tasks.db`.

