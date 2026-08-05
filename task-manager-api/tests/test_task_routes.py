from datetime import datetime, timedelta

import pytest

from models.task import Task

PAST = datetime.utcnow() - timedelta(days=2)
FUTURE = datetime.utcnow() + timedelta(days=2)


def test_get_tasks_returns_empty_list(client):
    response = client.get('/tasks')

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_tasks_enriches_with_names_and_overdue_flag(client, make_user, make_category, make_task):
    user = make_user(name='Alice')
    category = make_category(name='Work')
    make_task(title='Overdue', due_date=PAST, user_id=user.id, category_id=category.id, tags='a,b')
    make_task(title='Plain')

    body = client.get('/tasks').get_json()

    overdue, plain = body[0], body[1]
    assert overdue['overdue'] is True
    assert overdue['user_name'] == 'Alice'
    assert overdue['category_name'] == 'Work'
    assert overdue['tags'] == ['a', 'b']
    assert plain['overdue'] is False
    assert plain['user_name'] is None
    assert plain['category_name'] is None


@pytest.mark.parametrize('status, due_date, expected', [
    ('done', PAST, False),
    ('pending', FUTURE, False),
])
def test_get_tasks_marks_non_overdue_cases(client, make_task, status, due_date, expected):
    make_task(status=status, due_date=due_date)

    assert client.get('/tasks').get_json()[0]['overdue'] is expected


def test_get_tasks_returns_null_names_for_missing_relations(client, make_task):
    make_task(user_id=999, category_id=999)

    body = client.get('/tasks').get_json()[0]

    assert body['user_name'] is None
    assert body['category_name'] is None


def test_get_task_returns_task_with_overdue_flag(client, make_task):
    task = make_task(title='Single', due_date=PAST)

    response = client.get(f'/tasks/{task.id}')

    assert response.status_code == 200
    body = response.get_json()
    assert body['title'] == 'Single'
    assert body['overdue'] is True


@pytest.mark.parametrize('kwargs', [
    {'due_date': FUTURE},
    {'due_date': PAST, 'status': 'done'},
    {},
])
def test_get_task_reports_not_overdue(client, make_task, kwargs):
    task = make_task(**kwargs)

    assert client.get(f'/tasks/{task.id}').get_json()['overdue'] is False


def test_get_tasks_returns_500_when_query_fails(client, monkeypatch):
    monkeypatch.setattr(Task, 'query', None)

    response = client.get('/tasks')

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro interno'}


def test_get_task_returns_404_for_unknown_id(client):
    response = client.get('/tasks/999')

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Task não encontrada'}


def test_create_task_persists_full_payload(client, make_user, make_category):
    user = make_user()
    category = make_category()

    response = client.post('/tasks', json={
        'title': 'New task',
        'description': 'details',
        'status': 'in_progress',
        'priority': 1,
        'user_id': user.id,
        'category_id': category.id,
        'due_date': '2024-05-01',
        'tags': ['x', 'y'],
    })

    assert response.status_code == 201
    body = response.get_json()
    assert body['title'] == 'New task'
    assert body['status'] == 'in_progress'
    assert body['priority'] == 1
    assert body['due_date'] == '2024-05-01 00:00:00'
    assert body['tags'] == ['x', 'y']
    assert Task.query.count() == 1


def test_create_task_accepts_string_tags(client):
    response = client.post('/tasks', json={'title': 'Tagged', 'tags': 'x,y'})

    assert response.status_code == 201
    assert response.get_json()['tags'] == ['x', 'y']


@pytest.mark.parametrize('payload, status_code, error', [
    ({}, 400, 'Dados inválidos'),
    ({'title': ''}, 400, 'Título é obrigatório'),
    ({'title': 'ab'}, 400, 'Título muito curto'),
    ({'title': 'a' * 201}, 400, 'Título muito longo'),
    ({'title': 'valid', 'status': 'archived'}, 400, 'Status inválido'),
    ({'title': 'valid', 'priority': 0}, 400, 'Prioridade deve ser entre 1 e 5'),
    ({'title': 'valid', 'priority': 6}, 400, 'Prioridade deve ser entre 1 e 5'),
    ({'title': 'valid', 'due_date': '01/05/2024'}, 400, 'Formato de data inválido. Use YYYY-MM-DD'),
    ({'title': 'valid', 'user_id': 999}, 404, 'Usuário não encontrado'),
    ({'title': 'valid', 'category_id': 999}, 404, 'Categoria não encontrada'),
])
def test_create_task_rejects_invalid_payloads(client, payload, status_code, error):
    response = client.post('/tasks', json=payload)

    assert response.status_code == status_code
    assert response.get_json()['error'] == error
    assert Task.query.count() == 0


def test_create_task_returns_500_when_commit_fails(client, break_commit):
    break_commit()

    response = client.post('/tasks', json={'title': 'Doomed'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao criar task'}


def test_update_task_applies_all_supported_fields(client, make_task, make_user, make_category):
    task = make_task(due_date=PAST)
    user = make_user()
    category = make_category()

    response = client.put(f'/tasks/{task.id}', json={
        'title': 'Updated',
        'description': 'new description',
        'status': 'done',
        'priority': 5,
        'user_id': user.id,
        'category_id': category.id,
        'due_date': '2024-06-01',
        'tags': ['z'],
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body['title'] == 'Updated'
    assert body['description'] == 'new description'
    assert body['status'] == 'done'
    assert body['priority'] == 5
    assert body['user_id'] == user.id
    assert body['category_id'] == category.id
    assert body['due_date'] == '2024-06-01 00:00:00'
    assert body['tags'] == ['z']


def test_update_task_clears_relations_and_due_date(client, make_user, make_task):
    user = make_user()
    task = make_task(user_id=user.id, due_date=PAST)

    response = client.put(f'/tasks/{task.id}', json={
        'user_id': None,
        'category_id': None,
        'due_date': None,
        'tags': 'single',
    })

    body = response.get_json()
    assert body['user_id'] is None
    assert body['category_id'] is None
    assert body['due_date'] is None
    assert body['tags'] == ['single']


def test_update_task_returns_404_for_unknown_id(client):
    response = client.put('/tasks/999', json={'title': 'Updated'})

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Task não encontrada'}


@pytest.mark.parametrize('payload, status_code, error', [
    ({}, 400, 'Dados inválidos'),
    ({'title': 'ab'}, 400, 'Título muito curto'),
    ({'title': 'a' * 201}, 400, 'Título muito longo'),
    ({'status': 'archived'}, 400, 'Status inválido'),
    ({'priority': 9}, 400, 'Prioridade deve ser entre 1 e 5'),
    ({'due_date': '01/05/2024'}, 400, 'Formato de data inválido'),
    ({'user_id': 999}, 404, 'Usuário não encontrado'),
    ({'category_id': 999}, 404, 'Categoria não encontrada'),
])
def test_update_task_rejects_invalid_payloads(client, make_task, payload, status_code, error):
    task = make_task(title='Original')

    response = client.put(f'/tasks/{task.id}', json=payload)

    assert response.status_code == status_code
    assert response.get_json()['error'] == error
    assert Task.query.get(task.id).title == 'Original'


def test_update_task_returns_500_when_commit_fails(client, make_task, break_commit):
    task = make_task()
    break_commit()

    response = client.put(f'/tasks/{task.id}', json={'title': 'Updated'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao atualizar'}


def test_delete_task_returns_500_when_commit_fails(client, make_task, break_commit):
    task = make_task()
    break_commit()

    response = client.delete(f'/tasks/{task.id}')

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao deletar'}


def test_delete_task_removes_it(client, make_task):
    task = make_task()

    response = client.delete(f'/tasks/{task.id}')

    assert response.status_code == 200
    assert response.get_json() == {'message': 'Task deletada com sucesso'}
    assert Task.query.count() == 0


def test_delete_task_returns_404_for_unknown_id(client):
    response = client.delete('/tasks/999')

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Task não encontrada'}


def test_search_tasks_without_filters_returns_all(client, make_task):
    make_task(title='One')
    make_task(title='Two')

    body = client.get('/tasks/search').get_json()

    assert {t['title'] for t in body} == {'One', 'Two'}


def test_search_tasks_matches_title_or_description(client, make_task):
    make_task(title='Buy milk')
    make_task(title='Other', description='milk shake')
    make_task(title='Unrelated')

    body = client.get('/tasks/search?q=milk').get_json()

    assert {t['title'] for t in body} == {'Buy milk', 'Other'}


def test_search_tasks_filters_by_status_priority_and_user(client, make_user, make_task):
    user = make_user()
    match = make_task(title='Match', status='done', priority=1, user_id=user.id)
    make_task(title='Miss', status='pending', priority=1, user_id=user.id)

    body = client.get(f'/tasks/search?status=done&priority=1&user_id={user.id}').get_json()

    assert [t['id'] for t in body] == [match.id]


def test_task_stats_counts_by_status_and_overdue(client, make_task):
    make_task(title='P', status='pending')
    make_task(title='IP', status='in_progress')
    make_task(title='D', status='done')
    make_task(title='C', status='cancelled')
    make_task(title='Overdue', status='pending', due_date=PAST)
    make_task(title='Closed overdue', status='done', due_date=PAST)

    body = client.get('/tasks/stats').get_json()

    assert body == {
        'total': 6,
        'pending': 2,
        'in_progress': 1,
        'done': 2,
        'cancelled': 1,
        'overdue': 1,
        'completion_rate': 33.33,
    }


def test_task_stats_completion_rate_is_zero_without_tasks(client):
    assert client.get('/tasks/stats').get_json()['completion_rate'] == 0
