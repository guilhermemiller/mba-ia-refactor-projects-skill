import hashlib
from datetime import datetime, timedelta

import pytest

from models.task import Task
from models.user import User

PAST = datetime.utcnow() - timedelta(days=2)
FUTURE = datetime.utcnow() + timedelta(days=2)


def test_get_users_returns_task_counts(client, make_user, make_task):
    user = make_user()
    make_task(user_id=user.id)
    make_task(user_id=user.id)

    body = client.get('/users').get_json()

    assert len(body) == 1
    assert body[0]['task_count'] == 2
    assert 'password' not in body[0]


def test_get_user_includes_tasks(client, make_user, make_task):
    user = make_user()
    make_task(title='Mine', user_id=user.id)
    make_task(title='Other')

    response = client.get(f'/users/{user.id}')

    assert response.status_code == 200
    body = response.get_json()
    assert [t['title'] for t in body['tasks']] == ['Mine']


def test_get_user_returns_404_for_unknown_id(client):
    response = client.get('/users/999')

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Usuário não encontrado'}


def test_create_user_hashes_password_and_defaults_role(client):
    response = client.post('/users', json={
        'name': 'Alice',
        'email': 'alice@example.com',
        'password': 'secret',
    })

    assert response.status_code == 201
    body = response.get_json()
    assert body['role'] == 'user'
    assert body['password'] == hashlib.md5(b'secret').hexdigest()
    assert User.query.count() == 1


def test_create_user_accepts_explicit_role(client):
    response = client.post('/users', json={
        'name': 'Root',
        'email': 'root@example.com',
        'password': 'secret',
        'role': 'admin',
    })

    assert response.get_json()['role'] == 'admin'


@pytest.mark.parametrize('payload, status_code, error', [
    ({}, 400, 'Dados inválidos'),
    ({'email': 'a@b.com', 'password': 'secret'}, 400, 'Nome é obrigatório'),
    ({'name': 'Alice', 'password': 'secret'}, 400, 'Email é obrigatório'),
    ({'name': 'Alice', 'email': 'a@b.com'}, 400, 'Senha é obrigatória'),
    ({'name': 'Alice', 'email': 'invalid', 'password': 'secret'}, 400, 'Email inválido'),
    ({'name': 'Alice', 'email': 'a@b.com', 'password': 'abc'}, 400, 'Senha deve ter no mínimo 4 caracteres'),
    ({'name': 'Alice', 'email': 'a@b.com', 'password': 'secret', 'role': 'root'}, 400, 'Role inválido'),
])
def test_create_user_rejects_invalid_payloads(client, payload, status_code, error):
    response = client.post('/users', json=payload)

    assert response.status_code == status_code
    assert response.get_json()['error'] == error
    assert User.query.count() == 0


def test_create_user_rejects_duplicate_email(client, make_user):
    make_user(email='taken@example.com')

    response = client.post('/users', json={
        'name': 'Other',
        'email': 'taken@example.com',
        'password': 'secret',
    })

    assert response.status_code == 409
    assert response.get_json() == {'error': 'Email já cadastrado'}


def test_create_user_returns_500_when_commit_fails(client, break_commit):
    break_commit()

    response = client.post('/users', json={
        'name': 'Alice',
        'email': 'alice@example.com',
        'password': 'secret',
    })

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao criar usuário'}


def test_update_user_applies_all_supported_fields(client, make_user):
    user = make_user()

    response = client.put(f'/users/{user.id}', json={
        'name': 'Renamed',
        'email': 'renamed@example.com',
        'password': 'newpass',
        'role': 'manager',
        'active': False,
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body['name'] == 'Renamed'
    assert body['email'] == 'renamed@example.com'
    assert body['password'] == hashlib.md5(b'newpass').hexdigest()
    assert body['role'] == 'manager'
    assert body['active'] is False


def test_update_user_allows_keeping_own_email(client, make_user):
    user = make_user(email='same@example.com')

    response = client.put(f'/users/{user.id}', json={'email': 'same@example.com'})

    assert response.status_code == 200


def test_update_user_returns_404_for_unknown_id(client):
    response = client.put('/users/999', json={'name': 'Ghost'})

    assert response.status_code == 404


@pytest.mark.parametrize('payload, status_code, error', [
    ({}, 400, 'Dados inválidos'),
    ({'email': 'invalid'}, 400, 'Email inválido'),
    ({'password': 'abc'}, 400, 'Senha muito curta'),
    ({'role': 'root'}, 400, 'Role inválido'),
])
def test_update_user_rejects_invalid_payloads(client, make_user, payload, status_code, error):
    user = make_user(name='Original')

    response = client.put(f'/users/{user.id}', json=payload)

    assert response.status_code == status_code
    assert response.get_json()['error'] == error


def test_update_user_rejects_email_taken_by_another_user(client, make_user):
    make_user(email='taken@example.com')
    user = make_user(name='Other', email='other@example.com')

    response = client.put(f'/users/{user.id}', json={'email': 'taken@example.com'})

    assert response.status_code == 409
    assert response.get_json() == {'error': 'Email já cadastrado'}


def test_update_user_returns_500_when_commit_fails(client, make_user, break_commit):
    user = make_user()
    break_commit()

    response = client.put(f'/users/{user.id}', json={'name': 'Renamed'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao atualizar'}


def test_delete_user_returns_500_when_commit_fails(client, make_user, break_commit):
    user = make_user()
    break_commit()

    response = client.delete(f'/users/{user.id}')

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao deletar'}


def test_delete_user_also_deletes_their_tasks(client, make_user, make_task):
    user = make_user()
    make_task(user_id=user.id)
    make_task(title='Kept')

    response = client.delete(f'/users/{user.id}')

    assert response.status_code == 200
    assert User.query.count() == 0
    assert [t.title for t in Task.query.all()] == ['Kept']


def test_delete_user_returns_404_for_unknown_id(client):
    response = client.delete('/users/999')

    assert response.status_code == 404


def test_get_user_tasks_flags_overdue(client, make_user, make_task):
    user = make_user()
    make_task(title='Overdue', user_id=user.id, due_date=PAST)
    make_task(title='Future', user_id=user.id, due_date=FUTURE)
    make_task(title='Closed', user_id=user.id, due_date=PAST, status='cancelled')
    make_task(title='No due date', user_id=user.id)

    body = client.get(f'/users/{user.id}/tasks').get_json()

    assert {t['title']: t['overdue'] for t in body} == {
        'Overdue': True,
        'Future': False,
        'Closed': False,
        'No due date': False,
    }


def test_get_user_tasks_returns_404_for_unknown_user(client):
    response = client.get('/users/999/tasks')

    assert response.status_code == 404


def test_login_returns_token_for_valid_credentials(client, make_user):
    user = make_user(email='alice@example.com', password='secret')

    response = client.post('/login', json={'email': 'alice@example.com', 'password': 'secret'})

    assert response.status_code == 200
    body = response.get_json()
    assert body['token'] == f'fake-jwt-token-{user.id}'
    assert body['user']['email'] == 'alice@example.com'


@pytest.mark.parametrize('payload, status_code, error', [
    ({}, 400, 'Dados inválidos'),
    ({'email': 'alice@example.com'}, 400, 'Email e senha são obrigatórios'),
    ({'password': 'secret'}, 400, 'Email e senha são obrigatórios'),
    ({'email': 'ghost@example.com', 'password': 'secret'}, 401, 'Credenciais inválidas'),
    ({'email': 'alice@example.com', 'password': 'wrong'}, 401, 'Credenciais inválidas'),
])
def test_login_rejects_bad_requests(client, make_user, payload, status_code, error):
    make_user(email='alice@example.com', password='secret')

    response = client.post('/login', json=payload)

    assert response.status_code == status_code
    assert response.get_json()['error'] == error


def test_login_rejects_inactive_user(client, make_user):
    make_user(email='inactive@example.com', password='secret', active=False)

    response = client.post('/login', json={'email': 'inactive@example.com', 'password': 'secret'})

    assert response.status_code == 403
    assert response.get_json() == {'error': 'Usuário inativo'}
