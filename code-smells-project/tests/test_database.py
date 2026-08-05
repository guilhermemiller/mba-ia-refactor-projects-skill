import sqlite3

import database


def test_get_db_creates_all_tables(db):
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")

    tables = {row['name'] for row in cursor.fetchall()}
    assert {'produtos', 'usuarios', 'pedidos', 'itens_pedido'} <= tables


def test_get_db_seeds_products_and_users(db):
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM produtos')
    assert cursor.fetchone()[0] == 10

    cursor.execute('SELECT COUNT(*) FROM usuarios')
    assert cursor.fetchone()[0] == 3


def test_get_db_uses_row_factory_allowing_access_by_column_name(db):
    cursor = db.cursor()
    cursor.execute('SELECT nome, preco FROM produtos ORDER BY id LIMIT 1')

    row = cursor.fetchone()
    assert isinstance(row, sqlite3.Row)
    assert row['nome'] == 'Notebook Gamer'


def test_get_db_reuses_the_cached_connection(db):
    assert database.get_db() is db


def test_get_db_does_not_seed_twice(db):
    cursor = db.cursor()
    cursor.execute('DELETE FROM produtos WHERE id > 5')
    db.commit()

    database.get_db()

    cursor.execute('SELECT COUNT(*) FROM produtos')
    assert cursor.fetchone()[0] == 5
