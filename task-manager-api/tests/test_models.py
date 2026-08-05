import hashlib
from datetime import datetime, timedelta

import pytest

from database import db
from models.category import Category
from models.task import Task
from models.user import User


def test_task_to_dict_exposes_defaults_and_splits_tags(app, make_task):
    task = make_task(title='Ship it', description='desc', tags='a,b')

    data = task.to_dict()

    assert data['id'] == task.id
    assert data['title'] == 'Ship it'
    assert data['description'] == 'desc'
    assert data['status'] == 'pending'
    assert data['priority'] == 3
    assert data['tags'] == ['a', 'b']
    assert data['due_date'] is None
    assert data['created_at'] == str(task.created_at)
    assert data['updated_at'] == str(task.updated_at)


def test_task_to_dict_returns_empty_tag_list_when_unset(app, make_task):
    assert make_task().to_dict()['tags'] == []


def test_task_to_dict_stringifies_due_date(app, make_task):
    task = make_task(due_date=datetime(2024, 5, 1))

    assert task.to_dict()['due_date'] == '2024-05-01 00:00:00'


@pytest.mark.parametrize('status, expected', [
    ('pending', True),
    ('in_progress', True),
    ('done', True),
    ('cancelled', True),
    ('archived', False),
])
def test_task_validate_status(status, expected):
    assert Task().validate_status(status) is expected


@pytest.mark.parametrize('priority, expected', [
    (1, True),
    (5, True),
    (0, False),
    (6, False),
])
def test_task_validate_priority(priority, expected):
    assert Task().validate_priority(priority) is expected


def test_task_is_overdue_when_due_date_passed_and_still_open():
    task = Task()
    task.due_date = datetime.utcnow() - timedelta(days=1)
    task.status = 'pending'

    assert task.is_overdue() is True


@pytest.mark.parametrize('status', ['done', 'cancelled'])
def test_task_is_not_overdue_when_closed(status):
    task = Task()
    task.due_date = datetime.utcnow() - timedelta(days=1)
    task.status = status

    assert task.is_overdue() is False


def test_task_is_not_overdue_for_future_due_date():
    task = Task()
    task.due_date = datetime.utcnow() + timedelta(days=1)
    task.status = 'pending'

    assert task.is_overdue() is False


def test_task_is_not_overdue_without_due_date():
    assert Task().is_overdue() is False


def test_user_set_password_stores_md5_digest():
    user = User()
    user.set_password('secret')

    assert user.password == hashlib.md5(b'secret').hexdigest()


def test_user_check_password_accepts_matching_password():
    user = User()
    user.set_password('secret')

    assert user.check_password('secret') is True
    assert user.check_password('other') is False


@pytest.mark.parametrize('role, expected', [
    ('admin', True),
    ('user', False),
    ('manager', False),
])
def test_user_is_admin(role, expected):
    user = User()
    user.role = role

    assert user.is_admin() is expected


def test_user_to_dict_includes_defaults(app, make_user):
    user = make_user(name='Bob', email='bob@example.com', password='pwd')

    data = user.to_dict()

    assert data['id'] == user.id
    assert data['name'] == 'Bob'
    assert data['email'] == 'bob@example.com'
    assert data['password'] == hashlib.md5(b'pwd').hexdigest()
    assert data['role'] == 'user'
    assert data['active'] is True
    assert data['created_at'] == str(user.created_at)


def test_category_defaults_and_to_dict(app, make_category):
    category = make_category(name='Home', description='chores', color='#123456')

    data = category.to_dict()

    assert data['id'] == category.id
    assert data['name'] == 'Home'
    assert data['description'] == 'chores'
    assert data['color'] == '#123456'
    assert data['created_at'] == str(category.created_at)


def test_category_color_defaults_to_black(app):
    category = Category()
    category.name = 'Default'
    db.session.add(category)
    db.session.commit()

    assert category.to_dict()['color'] == '#000000'


def test_task_relationships_expose_user_and_category(app, make_user, make_category, make_task):
    user = make_user()
    category = make_category()
    task = make_task(user_id=user.id, category_id=category.id)

    assert task.user.id == user.id
    assert task.category.id == category.id
    assert user.tasks == [task]
    assert category.tasks == [task]
