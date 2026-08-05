"""Smoke tests for the composition root (app.py) and the seed script.

Both modules build their own Flask app bound to ``sqlite:///tasks.db`` inside the
instance folder, so they are imported once here and the database file is removed
afterwards.
"""
import os

import pytest

import app as app_module
import seed as seed_module
from models.category import Category
from models.task import Task
from models.user import User


@pytest.fixture(scope='module')
def real_app():
    app_module.app.config['TESTING'] = True
    yield app_module.app

    db_path = os.path.join(app_module.app.instance_path, 'tasks.db')
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def real_client(real_app):
    with real_app.app_context():
        app_module.db.create_all()
    return real_app.test_client()


def test_index_lists_api_metadata(real_client):
    response = real_client.get('/')

    assert response.status_code == 200
    assert response.get_json() == {'message': 'Task Manager API', 'version': '1.0'}


def test_health_reports_ok(real_client):
    response = real_client.get('/health')

    assert response.status_code == 200
    body = response.get_json()
    assert body['status'] == 'ok'
    assert body['timestamp']


def test_blueprints_are_registered(real_app):
    assert set(real_app.blueprints) == {'tasks', 'users', 'reports'}


def test_seed_data_populates_users_categories_and_tasks(real_client, capsys):
    seed_module.seed_data()

    out = capsys.readouterr().out
    assert 'Seed concluído com sucesso!' in out

    with app_module.app.app_context():
        assert User.query.count() == 3
        assert Category.query.count() == 4
        assert Task.query.count() == 10
        assert Task.query.filter(Task.tags.isnot(None)).count() == 3
        assert Task.query.filter(Task.due_date.isnot(None)).count() == 5


def test_seed_data_is_idempotent(real_client):
    seed_module.seed_data()
    seed_module.seed_data()

    with app_module.app.app_context():
        assert User.query.count() == 3
        assert Task.query.count() == 10
