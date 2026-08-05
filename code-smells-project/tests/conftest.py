import pytest

import database
from app import app as flask_app


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Points the module-level connection of database.py at a fresh temp file.

    ``database.get_db`` caches its connection in a module global, so both the
    path and the cached connection have to be reset around every test.
    """
    monkeypatch.setattr(database, 'db_path', str(tmp_path / 'loja.db'))
    monkeypatch.setattr(database, 'db_connection', None)

    connection = database.get_db()
    yield connection

    connection.close()


@pytest.fixture
def client(db):
    flask_app.config['TESTING'] = True
    return flask_app.test_client()


@pytest.fixture
def empty_db(db):
    cursor = db.cursor()
    for table in ('itens_pedido', 'pedidos', 'produtos', 'usuarios'):
        cursor.execute(f'DELETE FROM {table}')
    db.commit()
    return db


@pytest.fixture
def empty_client(empty_db):
    flask_app.config['TESTING'] = True
    return flask_app.test_client()
