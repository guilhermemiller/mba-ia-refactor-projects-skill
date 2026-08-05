from datetime import datetime, timedelta

from models.category import Category

PAST = datetime.utcnow() - timedelta(days=3)
FUTURE = datetime.utcnow() + timedelta(days=3)


def test_summary_report_on_empty_database(client):
    body = client.get('/reports/summary').get_json()

    assert body['overview'] == {'total_tasks': 0, 'total_users': 0, 'total_categories': 0}
    assert body['overdue'] == {'count': 0, 'tasks': []}
    assert body['user_productivity'] == []
    assert body['generated_at']


def test_summary_report_aggregates_statuses_priorities_and_overdue(client, make_user, make_category, make_task):
    user = make_user()
    make_category()
    make_task(title='Pending p1', status='pending', priority=1, user_id=user.id)
    make_task(title='In progress p2', status='in_progress', priority=2, user_id=user.id)
    make_task(title='Done p3', status='done', priority=3, user_id=user.id)
    make_task(title='Cancelled p4', status='cancelled', priority=4)
    make_task(title='Overdue p5', status='pending', priority=5, due_date=PAST)
    make_task(title='Future', status='pending', due_date=FUTURE)
    make_task(title='Closed overdue', status='done', due_date=PAST)

    body = client.get('/reports/summary').get_json()

    assert body['overview'] == {'total_tasks': 7, 'total_users': 1, 'total_categories': 1}
    assert body['tasks_by_status'] == {'pending': 3, 'in_progress': 1, 'done': 2, 'cancelled': 1}
    assert body['tasks_by_priority'] == {'critical': 1, 'high': 1, 'medium': 3, 'low': 1, 'minimal': 1}
    assert body['overdue']['count'] == 1
    assert body['overdue']['tasks'][0]['title'] == 'Overdue p5'
    assert body['overdue']['tasks'][0]['days_overdue'] == 3
    assert body['recent_activity'] == {'tasks_created_last_7_days': 7, 'tasks_completed_last_7_days': 2}
    assert body['user_productivity'] == [{
        'user_id': user.id,
        'user_name': user.name,
        'total_tasks': 3,
        'completed_tasks': 1,
        'completion_rate': 33.33,
    }]


def test_summary_report_reports_zero_completion_rate_for_user_without_tasks(client, make_user):
    user = make_user()

    body = client.get('/reports/summary').get_json()

    assert body['user_productivity'] == [{
        'user_id': user.id,
        'user_name': user.name,
        'total_tasks': 0,
        'completed_tasks': 0,
        'completion_rate': 0,
    }]


def test_user_report_counts_statuses_priorities_and_overdue(client, make_user, make_task):
    user = make_user(name='Alice', email='alice@example.com')
    make_task(title='Done', status='done', priority=1, user_id=user.id)
    make_task(title='Pending', status='pending', priority=2, user_id=user.id)
    make_task(title='In progress', status='in_progress', priority=3, user_id=user.id)
    make_task(title='Cancelled', status='cancelled', priority=4, user_id=user.id)
    make_task(title='Overdue', status='pending', priority=5, user_id=user.id, due_date=PAST)
    make_task(title='Someone else', status='done', user_id=None)

    body = client.get(f'/reports/user/{user.id}').get_json()

    assert body['user'] == {'id': user.id, 'name': 'Alice', 'email': 'alice@example.com'}
    assert body['statistics'] == {
        'total_tasks': 5,
        'done': 1,
        'pending': 2,
        'in_progress': 1,
        'cancelled': 1,
        'overdue': 1,
        'high_priority': 2,
        'completion_rate': 20.0,
    }


def test_user_report_without_tasks_has_zero_completion_rate(client, make_user):
    user = make_user()

    body = client.get(f'/reports/user/{user.id}').get_json()

    assert body['statistics']['total_tasks'] == 0
    assert body['statistics']['completion_rate'] == 0


def test_user_report_returns_404_for_unknown_user(client):
    response = client.get('/reports/user/999')

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Usuário não encontrado'}


def test_get_categories_includes_task_counts(client, make_category, make_task):
    category = make_category(name='Work')
    make_category(name='Empty')
    make_task(category_id=category.id)

    body = client.get('/categories').get_json()

    assert {c['name']: c['task_count'] for c in body} == {'Work': 1, 'Empty': 0}


def test_create_category_uses_defaults(client):
    response = client.post('/categories', json={'name': 'Home'})

    assert response.status_code == 201
    body = response.get_json()
    assert body['name'] == 'Home'
    assert body['description'] == ''
    assert body['color'] == '#000000'


def test_create_category_accepts_description_and_color(client):
    response = client.post('/categories', json={
        'name': 'Home',
        'description': 'chores',
        'color': '#abcdef',
    })

    body = response.get_json()
    assert body['description'] == 'chores'
    assert body['color'] == '#abcdef'


def test_create_category_requires_payload(client):
    response = client.post('/categories', json={})

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Dados inválidos'}


def test_create_category_requires_name(client):
    response = client.post('/categories', json={'description': 'no name'})

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Nome é obrigatório'}


def test_create_category_returns_500_when_commit_fails(client, break_commit):
    break_commit()

    response = client.post('/categories', json={'name': 'Doomed'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao criar categoria'}


def test_update_category_applies_fields(client, make_category):
    category = make_category()

    response = client.put(f'/categories/{category.id}', json={
        'name': 'Renamed',
        'description': 'updated',
        'color': '#111111',
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body['name'] == 'Renamed'
    assert body['description'] == 'updated'
    assert body['color'] == '#111111'


def test_update_category_returns_404_for_unknown_id(client):
    response = client.put('/categories/999', json={'name': 'Ghost'})

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Categoria não encontrada'}


def test_update_category_returns_500_when_commit_fails(client, make_category, break_commit):
    category = make_category()
    break_commit()

    response = client.put(f'/categories/{category.id}', json={'name': 'Renamed'})

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao atualizar'}


def test_delete_category_returns_500_when_commit_fails(client, make_category, break_commit):
    category = make_category()
    break_commit()

    response = client.delete(f'/categories/{category.id}')

    assert response.status_code == 500
    assert response.get_json() == {'error': 'Erro ao deletar'}


def test_delete_category_removes_it(client, make_category):
    category = make_category()

    response = client.delete(f'/categories/{category.id}')

    assert response.status_code == 200
    assert response.get_json() == {'message': 'Categoria deletada'}
    assert Category.query.count() == 0


def test_delete_category_returns_404_for_unknown_id(client):
    response = client.delete('/categories/999')

    assert response.status_code == 404
    assert response.get_json() == {'error': 'Categoria não encontrada'}
