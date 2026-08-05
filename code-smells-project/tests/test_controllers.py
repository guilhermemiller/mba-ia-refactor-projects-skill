import pytest

import controllers
import models


def _raise(message):
    """Builds a stub that raises, to exercise the broad ``except`` handlers."""
    def _raiser(*args, **kwargs):
        raise Exception(message)

    return _raiser


@pytest.fixture
def produto(empty_db):
    produto_id = models.criar_produto('Teclado', 'Teclado mecânico', 199.9, 5, 'informatica')
    return models.get_produto_por_id(produto_id)


@pytest.fixture
def usuario(empty_db):
    usuario_id = models.criar_usuario('Ana', 'ana@example.com', 'segredo')
    return models.get_usuario_por_id(usuario_id)


def test_listar_produtos_returns_catalog(client):
    response = client.get('/produtos')

    assert response.status_code == 200
    body = response.get_json()
    assert body['sucesso'] is True
    assert len(body['dados']) == 10


def test_listar_produtos_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_todos_produtos', _raise('boom'))

    response = client.get('/produtos')

    assert response.status_code == 500
    assert response.get_json() == {'erro': 'boom'}


def test_buscar_produto_returns_single_product(produto, empty_client):
    response = empty_client.get(f"/produtos/{produto['id']}")

    assert response.status_code == 200
    assert response.get_json()['dados']['nome'] == 'Teclado'


def test_buscar_produto_returns_404_when_missing(empty_client):
    response = empty_client.get('/produtos/999')

    assert response.status_code == 404
    assert response.get_json() == {'erro': 'Produto não encontrado', 'sucesso': False}


def test_buscar_produto_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_produto_por_id', _raise('boom'))

    assert client.get('/produtos/1').status_code == 500


def test_criar_produto_persists_and_returns_id(empty_client):
    response = empty_client.post('/produtos', json={
        'nome': 'Monitor',
        'descricao': '27 polegadas',
        'preco': 1500.0,
        'estoque': 3,
        'categoria': 'informatica',
    })

    assert response.status_code == 201
    produto_id = response.get_json()['dados']['id']
    assert models.get_produto_por_id(produto_id)['nome'] == 'Monitor'


def test_criar_produto_uses_default_category_and_description(empty_client):
    response = empty_client.post('/produtos', json={'nome': 'Item', 'preco': 10, 'estoque': 1})

    produto = models.get_produto_por_id(response.get_json()['dados']['id'])
    assert produto['categoria'] == 'geral'
    assert produto['descricao'] == ''


@pytest.mark.parametrize('payload, error', [
    ({}, 'Dados inválidos'),
    ({'preco': 1, 'estoque': 1}, 'Nome é obrigatório'),
    ({'nome': 'Item', 'estoque': 1}, 'Preço é obrigatório'),
    ({'nome': 'Item', 'preco': 1}, 'Estoque é obrigatório'),
    ({'nome': 'Item', 'preco': -1, 'estoque': 1}, 'Preço não pode ser negativo'),
    ({'nome': 'Item', 'preco': 1, 'estoque': -1}, 'Estoque não pode ser negativo'),
    ({'nome': 'I', 'preco': 1, 'estoque': 1}, 'Nome muito curto'),
    ({'nome': 'I' * 201, 'preco': 1, 'estoque': 1}, 'Nome muito longo'),
])
def test_criar_produto_rejects_invalid_payloads(empty_client, payload, error):
    response = empty_client.post('/produtos', json=payload)

    assert response.status_code == 400
    assert response.get_json()['erro'] == error
    assert models.get_todos_produtos() == []


def test_criar_produto_rejects_unknown_category(empty_client):
    response = empty_client.post('/produtos', json={
        'nome': 'Item',
        'preco': 1,
        'estoque': 1,
        'categoria': 'aleatoria',
    })

    assert response.status_code == 400
    assert response.get_json()['erro'].startswith('Categoria inválida')


def test_criar_produto_returns_500_on_failure(empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'criar_produto', _raise('boom'))

    response = empty_client.post('/produtos', json={'nome': 'Item', 'preco': 1, 'estoque': 1})

    assert response.status_code == 500
    assert response.get_json() == {'erro': 'boom'}


def test_atualizar_produto_updates_fields(produto, empty_client):
    response = empty_client.put(f"/produtos/{produto['id']}", json={
        'nome': 'Atualizado',
        'descricao': 'nova',
        'preco': 50.0,
        'estoque': 2,
        'categoria': 'geral',
    })

    assert response.status_code == 200
    assert models.get_produto_por_id(produto['id'])['nome'] == 'Atualizado'


def test_atualizar_produto_returns_404_when_missing(empty_client):
    response = empty_client.put('/produtos/999', json={'nome': 'X', 'preco': 1, 'estoque': 1})

    assert response.status_code == 404
    assert response.get_json() == {'erro': 'Produto não encontrado'}


@pytest.mark.parametrize('payload, error', [
    ({}, 'Dados inválidos'),
    ({'preco': 1, 'estoque': 1}, 'Nome é obrigatório'),
    ({'nome': 'Item', 'estoque': 1}, 'Preço é obrigatório'),
    ({'nome': 'Item', 'preco': 1}, 'Estoque é obrigatório'),
    ({'nome': 'Item', 'preco': -1, 'estoque': 1}, 'Preço não pode ser negativo'),
    ({'nome': 'Item', 'preco': 1, 'estoque': -1}, 'Estoque não pode ser negativo'),
])
def test_atualizar_produto_rejects_invalid_payloads(produto, empty_client, payload, error):
    response = empty_client.put(f"/produtos/{produto['id']}", json=payload)

    assert response.status_code == 400
    assert response.get_json()['erro'] == error
    assert models.get_produto_por_id(produto['id'])['nome'] == 'Teclado'


def test_atualizar_produto_returns_500_on_failure(produto, empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'atualizar_produto', _raise('boom'))

    response = empty_client.put(f"/produtos/{produto['id']}", json={
        'nome': 'X', 'preco': 1, 'estoque': 1,
    })

    assert response.status_code == 500


def test_deletar_produto_removes_it(produto, empty_client):
    response = empty_client.delete(f"/produtos/{produto['id']}")

    assert response.status_code == 200
    assert models.get_produto_por_id(produto['id']) is None


def test_deletar_produto_returns_404_when_missing(empty_client):
    response = empty_client.delete('/produtos/999')

    assert response.status_code == 404


def test_deletar_produto_returns_500_on_failure(produto, empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'deletar_produto', _raise('boom'))

    assert empty_client.delete(f"/produtos/{produto['id']}").status_code == 500


def test_buscar_produtos_applies_query_string_filters(client):
    response = client.get('/produtos/busca?q=Mouse&categoria=informatica&preco_min=10&preco_max=1000')

    assert response.status_code == 200
    body = response.get_json()
    assert body['total'] == 1
    assert body['dados'][0]['nome'] == 'Mouse Wireless'


def test_buscar_produtos_returns_500_for_invalid_price(client):
    response = client.get('/produtos/busca?preco_min=abc')

    assert response.status_code == 500
    assert 'erro' in response.get_json()


def test_listar_usuarios_exposes_password_hashes(client):
    response = client.get('/usuarios')

    assert response.status_code == 200
    assert 'senha' in response.get_json()['dados'][0]


def test_listar_usuarios_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_todos_usuarios', _raise('boom'))

    assert client.get('/usuarios').status_code == 500


def test_buscar_usuario_returns_user(usuario, empty_client):
    response = empty_client.get(f"/usuarios/{usuario['id']}")

    assert response.status_code == 200
    assert response.get_json()['dados']['email'] == 'ana@example.com'


def test_buscar_usuario_returns_404_when_missing(empty_client):
    response = empty_client.get('/usuarios/999')

    assert response.status_code == 404
    assert response.get_json() == {'erro': 'Usuário não encontrado'}


def test_buscar_usuario_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_usuario_por_id', _raise('boom'))

    assert client.get('/usuarios/1').status_code == 500


def test_criar_usuario_persists_user(empty_client):
    response = empty_client.post('/usuarios', json={
        'nome': 'Bruno',
        'email': 'bruno@example.com',
        'senha': 'segredo',
    })

    assert response.status_code == 201
    usuario_id = response.get_json()['dados']['id']
    assert models.get_usuario_por_id(usuario_id)['nome'] == 'Bruno'


@pytest.mark.parametrize('payload, error', [
    ({}, 'Dados inválidos'),
    ({'email': 'a@b.com', 'senha': 'x'}, 'Nome, email e senha são obrigatórios'),
    ({'nome': 'Bruno', 'senha': 'x'}, 'Nome, email e senha são obrigatórios'),
    ({'nome': 'Bruno', 'email': 'a@b.com'}, 'Nome, email e senha são obrigatórios'),
])
def test_criar_usuario_rejects_invalid_payloads(empty_client, payload, error):
    response = empty_client.post('/usuarios', json=payload)

    assert response.status_code == 400
    assert response.get_json()['erro'] == error
    assert models.get_todos_usuarios() == []


def test_criar_usuario_returns_500_on_failure(empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'criar_usuario', _raise('boom'))

    response = empty_client.post('/usuarios', json={
        'nome': 'Bruno', 'email': 'a@b.com', 'senha': 'x',
    })

    assert response.status_code == 500


def test_login_returns_user_on_valid_credentials(usuario, empty_client):
    response = empty_client.post('/login', json={'email': 'ana@example.com', 'senha': 'segredo'})

    assert response.status_code == 200
    body = response.get_json()
    assert body['sucesso'] is True
    assert body['dados']['id'] == usuario['id']


def test_login_returns_401_for_wrong_credentials(usuario, empty_client):
    response = empty_client.post('/login', json={'email': 'ana@example.com', 'senha': 'errada'})

    assert response.status_code == 401
    assert response.get_json()['sucesso'] is False


@pytest.mark.parametrize('payload', [
    {'email': 'ana@example.com'},
    {'senha': 'segredo'},
    {},
])
def test_login_requires_email_and_password(empty_client, payload):
    response = empty_client.post('/login', json=payload)

    assert response.status_code == 400
    assert response.get_json() == {'erro': 'Email e senha são obrigatórios'}


def test_login_returns_500_on_failure(empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'login_usuario', _raise('boom'))

    response = empty_client.post('/login', json={'email': 'a@b.com', 'senha': 'x'})

    assert response.status_code == 500


def test_criar_pedido_creates_order_and_notifies(produto, usuario, empty_client, capsys):
    response = empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': produto['id'], 'quantidade': 2}],
    })

    assert response.status_code == 201
    body = response.get_json()
    assert body['dados']['total'] == pytest.approx(399.8)

    out = capsys.readouterr().out
    assert 'ENVIANDO EMAIL' in out
    assert 'ENVIANDO SMS' in out
    assert 'ENVIANDO PUSH' in out


@pytest.mark.parametrize('payload, error', [
    ({}, 'Dados inválidos'),
    ({'itens': [{'produto_id': 1, 'quantidade': 1}]}, 'Usuario ID é obrigatório'),
    ({'usuario_id': 1}, 'Pedido deve ter pelo menos 1 item'),
    ({'usuario_id': 1, 'itens': []}, 'Pedido deve ter pelo menos 1 item'),
])
def test_criar_pedido_rejects_invalid_payloads(empty_client, payload, error):
    response = empty_client.post('/pedidos', json=payload)

    assert response.status_code == 400
    assert response.get_json()['erro'] == error


def test_criar_pedido_propagates_domain_error(usuario, empty_client):
    response = empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': 999, 'quantidade': 1}],
    })

    assert response.status_code == 400
    assert response.get_json() == {'erro': 'Produto 999 não encontrado', 'sucesso': False}


def test_criar_pedido_returns_500_on_failure(usuario, empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'criar_pedido', _raise('boom'))

    response = empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': 1, 'quantidade': 1}],
    })

    assert response.status_code == 500


def test_listar_pedidos_usuario_returns_orders(produto, usuario, empty_client):
    empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })

    response = empty_client.get(f"/pedidos/usuario/{usuario['id']}")

    assert response.status_code == 200
    assert len(response.get_json()['dados']) == 1


def test_listar_pedidos_usuario_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_pedidos_usuario', _raise('boom'))

    assert client.get('/pedidos/usuario/1').status_code == 500


def test_listar_todos_pedidos_returns_orders(produto, usuario, empty_client):
    empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })

    response = empty_client.get('/pedidos')

    assert response.status_code == 200
    assert len(response.get_json()['dados']) == 1


def test_listar_todos_pedidos_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'get_todos_pedidos', _raise('boom'))

    assert client.get('/pedidos').status_code == 500


@pytest.mark.parametrize('status, expected_notification', [
    ('aprovado', 'foi aprovado'),
    ('cancelado', 'cancelado. Devolver estoque'),
])
def test_atualizar_status_pedido_notifies_on_transition(
    produto, usuario, empty_client, capsys, status, expected_notification
):
    created = empty_client.post('/pedidos', json={
        'usuario_id': usuario['id'],
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })
    pedido_id = created.get_json()['dados']['pedido_id']
    capsys.readouterr()

    response = empty_client.put(f'/pedidos/{pedido_id}/status', json={'status': status})

    assert response.status_code == 200
    assert expected_notification in capsys.readouterr().out
    assert models.get_todos_pedidos()[0]['status'] == status


def test_atualizar_status_pedido_rejects_unknown_status(empty_client):
    response = empty_client.put('/pedidos/1/status', json={'status': 'entregando'})

    assert response.status_code == 400
    assert response.get_json() == {'erro': 'Status inválido'}


def test_atualizar_status_pedido_returns_500_on_failure(empty_client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'atualizar_status_pedido', _raise('boom'))

    response = empty_client.put('/pedidos/1/status', json={'status': 'aprovado'})

    assert response.status_code == 500


def test_relatorio_vendas_returns_report(client):
    response = client.get('/relatorios/vendas')

    assert response.status_code == 200
    assert response.get_json()['dados']['total_pedidos'] == 0


def test_relatorio_vendas_returns_500_on_failure(client, monkeypatch):
    monkeypatch.setattr(controllers.models, 'relatorio_vendas', _raise('boom'))

    assert client.get('/relatorios/vendas').status_code == 500


def test_health_check_reports_counts_and_leaks_configuration(client):
    response = client.get('/health')

    assert response.status_code == 200
    body = response.get_json()
    assert body['status'] == 'ok'
    assert body['counts'] == {'produtos': 10, 'usuarios': 3, 'pedidos': 0}
    assert body['secret_key'] == 'minha-chave-super-secreta-123'


def test_health_check_returns_500_when_database_fails(client, monkeypatch):
    monkeypatch.setattr(controllers, 'get_db', _raise('sem banco'))

    response = client.get('/health')

    assert response.status_code == 500
    assert response.get_json() == {'status': 'erro', 'detalhes': 'sem banco'}
