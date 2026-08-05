import models
from app import app


def test_index_lists_available_endpoints(client):
    response = client.get('/')

    assert response.status_code == 200
    body = response.get_json()
    assert body['versao'] == '1.0.0'
    assert set(body['endpoints']) == {'produtos', 'usuarios', 'pedidos', 'login', 'relatorios', 'health'}


def test_debug_mode_and_secret_key_are_hardcoded():
    assert app.config['DEBUG'] is True
    assert app.config['SECRET_KEY'] == 'minha-chave-super-secreta-123'


def test_every_documented_route_is_registered():
    rules = {(rule.rule, method) for rule in app.url_map.iter_rules() for method in rule.methods}

    assert ('/produtos', 'GET') in rules
    assert ('/produtos', 'POST') in rules
    assert ('/produtos/busca', 'GET') in rules
    assert ('/produtos/<int:id>', 'PUT') in rules
    assert ('/produtos/<int:id>', 'DELETE') in rules
    assert ('/usuarios', 'GET') in rules
    assert ('/login', 'POST') in rules
    assert ('/pedidos', 'POST') in rules
    assert ('/pedidos/usuario/<int:usuario_id>', 'GET') in rules
    assert ('/pedidos/<int:pedido_id>/status', 'PUT') in rules
    assert ('/relatorios/vendas', 'GET') in rules
    assert ('/health', 'GET') in rules


def test_reset_db_wipes_every_table_without_authentication(client):
    response = client.post('/admin/reset-db')

    assert response.status_code == 200
    assert response.get_json() == {'mensagem': 'Banco de dados resetado', 'sucesso': True}
    assert models.get_todos_produtos() == []
    assert models.get_todos_usuarios() == []


def test_admin_query_runs_arbitrary_select(client):
    response = client.post('/admin/query', json={'sql': 'SELECT nome FROM produtos ORDER BY id LIMIT 1'})

    assert response.status_code == 200
    assert response.get_json()['dados'] == [{'nome': 'Notebook Gamer'}]


def test_admin_query_commits_arbitrary_writes(client):
    response = client.post('/admin/query', json={'sql': 'DELETE FROM produtos'})

    assert response.status_code == 200
    assert response.get_json() == {'mensagem': 'Query executada', 'sucesso': True}
    assert models.get_todos_produtos() == []


def test_admin_query_requires_a_statement(client):
    response = client.post('/admin/query', json={})

    assert response.status_code == 400
    assert response.get_json() == {'erro': 'Query não informada'}


def test_admin_query_returns_500_for_invalid_sql(client):
    response = client.post('/admin/query', json={'sql': 'SELECT * FROM inexistente'})

    assert response.status_code == 500
    assert 'erro' in response.get_json()
