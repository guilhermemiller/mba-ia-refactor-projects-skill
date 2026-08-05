import pytest
from flask import Flask

from database import db
from models.category import Category
from models.task import Task
from models.user import User
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True

    db.init_app(app)
    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def break_commit(monkeypatch):
    """Returns an activator that makes ``db.session.commit()`` fail from then on.

    Used to exercise the rollback branches of the routes after the test has
    already persisted its fixtures.
    """
    def _fail():
        raise RuntimeError('commit failed')

    def _activate():
        monkeypatch.setattr(db.session, 'commit', _fail)

    return _activate


@pytest.fixture
def make_user():
    def _make_user(name='Alice', email='alice@example.com', password='secret', role='user', active=True):
        user = User()
        user.name = name
        user.email = email
        user.set_password(password)
        user.role = role
        user.active = active
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture
def make_category():
    def _make_category(name='Work', description='', color='#ffffff'):
        category = Category()
        category.name = name
        category.description = description
        category.color = color
        db.session.add(category)
        db.session.commit()
        return category

    return _make_category


@pytest.fixture
def make_task():
    def _make_task(title='Write tests', **kwargs):
        task = Task()
        task.title = title
        for field, value in kwargs.items():
            setattr(task, field, value)
        db.session.add(task)
        db.session.commit()
        return task

    return _make_task
