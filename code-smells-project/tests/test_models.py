import pytest

import models

PRODUCT_FIELDS = {'id', 'nome', 'descricao', 'preco', 'estoque', 'categoria', 'ativo', 'criado_em'}


@pytest.fixture
def produto(empty_db):
    produto_id = models.criar_produto('Teclado', 'Teclado mecânico', 199.9, 5, 'informatica')
    return models.get_produto_por_id(produto_id)


@pytest.fixture
def usuario(empty_db):
    usuario_id = models.criar_usuario('Ana', 'ana@example.com', 'segredo')
    return models.get_usuario_por_id(usuario_id)


def test_get_todos_produtos_returns_seeded_catalog(db):
    produtos = models.get_todos_produtos()

    assert len(produtos) == 10
    assert set(produtos[0]) == PRODUCT_FIELDS


def test_get_todos_produtos_returns_empty_list_without_rows(empty_db):
    assert models.get_todos_produtos() == []


def test_criar_produto_returns_new_id_and_persists_fields(empty_db):
    produto_id = models.criar_produto('Mouse', 'Sem fio', 89.9, 12, 'informatica')

    produto = models.get_produto_por_id(produto_id)
    assert produto['id'] == produto_id
    assert produto['nome'] == 'Mouse'
    assert produto['descricao'] == 'Sem fio'
    assert produto['preco'] == 89.9
    assert produto['estoque'] == 12
    assert produto['categoria'] == 'informatica'
    assert produto['ativo'] == 1


def test_get_produto_por_id_returns_none_when_missing(empty_db):
    assert models.get_produto_por_id(999) is None


def test_atualizar_produto_overwrites_all_fields(produto):
    assert models.atualizar_produto(produto['id'], 'Novo', 'Nova descrição', 10.5, 1, 'geral') is True

    atualizado = models.get_produto_por_id(produto['id'])
    assert atualizado['nome'] == 'Novo'
    assert atualizado['descricao'] == 'Nova descrição'
    assert atualizado['preco'] == 10.5
    assert atualizado['estoque'] == 1
    assert atualizado['categoria'] == 'geral'


def test_deletar_produto_removes_the_row(produto):
    assert models.deletar_produto(produto['id']) is True
    assert models.get_produto_por_id(produto['id']) is None


def test_get_todos_usuarios_exposes_stored_password(db):
    usuarios = models.get_todos_usuarios()

    assert len(usuarios) == 3
    assert usuarios[0]['senha'] == 'admin123'


def test_get_todos_usuarios_returns_empty_list_without_rows(empty_db):
    assert models.get_todos_usuarios() == []


def test_criar_usuario_defaults_to_cliente(usuario):
    assert usuario['nome'] == 'Ana'
    assert usuario['email'] == 'ana@example.com'
    assert usuario['tipo'] == 'cliente'


def test_criar_usuario_accepts_explicit_type(empty_db):
    usuario_id = models.criar_usuario('Root', 'root@example.com', 'x', 'admin')

    assert models.get_usuario_por_id(usuario_id)['tipo'] == 'admin'


def test_get_usuario_por_id_returns_none_when_missing(empty_db):
    assert models.get_usuario_por_id(999) is None


def test_login_usuario_returns_public_fields_on_success(usuario):
    result = models.login_usuario('ana@example.com', 'segredo')

    assert result == {
        'id': usuario['id'],
        'nome': 'Ana',
        'email': 'ana@example.com',
        'tipo': 'cliente',
    }


def test_login_usuario_returns_none_for_wrong_password(usuario):
    assert models.login_usuario('ana@example.com', 'errado') is None


def test_criar_pedido_computes_total_and_decrements_stock(produto, usuario):
    result = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 2}])

    assert result['total'] == pytest.approx(399.8)
    assert models.get_produto_por_id(produto['id'])['estoque'] == 3


def test_criar_pedido_rejects_unknown_product(usuario):
    result = models.criar_pedido(usuario['id'], [{'produto_id': 999, 'quantidade': 1}])

    assert result == {'erro': 'Produto 999 não encontrado'}


def test_criar_pedido_rejects_insufficient_stock(produto, usuario):
    result = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 99}])

    assert result == {'erro': 'Estoque insuficiente para Teclado'}
    assert models.get_produto_por_id(produto['id'])['estoque'] == 5


def test_get_pedidos_usuario_includes_items_with_product_names(produto, usuario):
    pedido = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])

    pedidos = models.get_pedidos_usuario(usuario['id'])

    assert len(pedidos) == 1
    assert pedidos[0]['id'] == pedido['pedido_id']
    assert pedidos[0]['status'] == 'pendente'
    assert pedidos[0]['itens'] == [{
        'produto_id': produto['id'],
        'produto_nome': 'Teclado',
        'quantidade': 1,
        'preco_unitario': produto['preco'],
    }]


def test_get_pedidos_usuario_returns_empty_list_for_user_without_orders(usuario):
    assert models.get_pedidos_usuario(usuario['id']) == []


def test_get_pedidos_usuario_labels_deleted_products_as_unknown(produto, usuario):
    models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    models.deletar_produto(produto['id'])

    itens = models.get_pedidos_usuario(usuario['id'])[0]['itens']

    assert itens[0]['produto_nome'] == 'Desconhecido'


def test_get_todos_pedidos_returns_orders_of_every_user(produto, usuario):
    outro_id = models.criar_usuario('Bruno', 'bruno@example.com', 'x')
    models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    models.criar_pedido(outro_id, [{'produto_id': produto['id'], 'quantidade': 1}])

    pedidos = models.get_todos_pedidos()

    assert {p['usuario_id'] for p in pedidos} == {usuario['id'], outro_id}
    assert all(len(p['itens']) == 1 for p in pedidos)


def test_get_todos_pedidos_labels_deleted_products_as_unknown(produto, usuario):
    models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    models.deletar_produto(produto['id'])

    assert models.get_todos_pedidos()[0]['itens'][0]['produto_nome'] == 'Desconhecido'


def test_atualizar_status_pedido_changes_the_status(produto, usuario):
    pedido = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])

    assert models.atualizar_status_pedido(pedido['pedido_id'], 'aprovado') is True
    assert models.get_todos_pedidos()[0]['status'] == 'aprovado'


def test_relatorio_vendas_on_empty_database(empty_db):
    assert models.relatorio_vendas() == {
        'total_pedidos': 0,
        'faturamento_bruto': 0,
        'desconto_aplicavel': 0,
        'faturamento_liquido': 0,
        'pedidos_pendentes': 0,
        'pedidos_aprovados': 0,
        'pedidos_cancelados': 0,
        'ticket_medio': 0,
    }


def test_relatorio_vendas_counts_orders_by_status(produto, usuario):
    pendente = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    aprovado = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    cancelado = models.criar_pedido(usuario['id'], [{'produto_id': produto['id'], 'quantidade': 1}])
    models.atualizar_status_pedido(aprovado['pedido_id'], 'aprovado')
    models.atualizar_status_pedido(cancelado['pedido_id'], 'cancelado')

    relatorio = models.relatorio_vendas()

    assert relatorio['total_pedidos'] == 3
    assert relatorio['pedidos_pendentes'] == 1
    assert relatorio['pedidos_aprovados'] == 1
    assert relatorio['pedidos_cancelados'] == 1
    assert relatorio['ticket_medio'] == pytest.approx(199.9)
    assert pendente['pedido_id'] != aprovado['pedido_id']


@pytest.mark.parametrize('preco, quantidade, expected_discount_rate', [
    (600.0, 2, 0.02),
    (3000.0, 2, 0.05),
    (6000.0, 2, 0.10),
])
def test_relatorio_vendas_applies_tiered_discount(empty_db, usuario, preco, quantidade, expected_discount_rate):
    produto_id = models.criar_produto('Item', '', preco, 100, 'geral')
    models.criar_pedido(usuario['id'], [{'produto_id': produto_id, 'quantidade': quantidade}])

    relatorio = models.relatorio_vendas()

    faturamento = preco * quantidade
    assert relatorio['faturamento_bruto'] == pytest.approx(faturamento)
    assert relatorio['desconto_aplicavel'] == pytest.approx(round(faturamento * expected_discount_rate, 2))
    assert relatorio['faturamento_liquido'] == pytest.approx(
        round(faturamento - faturamento * expected_discount_rate, 2)
    )


def test_relatorio_vendas_without_discount_below_first_tier(empty_db, usuario):
    produto_id = models.criar_produto('Item', '', 100.0, 10, 'geral')
    models.criar_pedido(usuario['id'], [{'produto_id': produto_id, 'quantidade': 1}])

    assert models.relatorio_vendas()['desconto_aplicavel'] == 0


def test_buscar_produtos_without_filters_returns_everything(db):
    assert len(models.buscar_produtos('')) == 10


def test_buscar_produtos_matches_name_or_description(db):
    resultados = models.buscar_produtos('Mouse')

    assert [p['nome'] for p in resultados] == ['Mouse Wireless']


def test_buscar_produtos_filters_by_category_and_price_range(db):
    resultados = models.buscar_produtos('', categoria='informatica', preco_min=200, preco_max=500)

    assert {p['nome'] for p in resultados} == {'Teclado Mecânico', 'Webcam HD', 'SSD 1TB'}
    assert set(resultados[0]) == PRODUCT_FIELDS
