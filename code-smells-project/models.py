from database import get_db
from db_utils import (
    buscar_todos,
    buscar_um,
    contar,
    executar,
    map_produto,
    map_usuario,
    map_usuario_publico,
    montar_pedidos,
)

def get_todos_produtos():
    rows = buscar_todos("SELECT * FROM produtos")
    return [map_produto(row) for row in rows]

def get_produto_por_id(id):
    row = buscar_um("SELECT * FROM produtos WHERE id = " + str(id))
    if row:
        return map_produto(row)
    return None

def criar_produto(nome, descricao, preco, estoque, categoria):
    cursor = executar(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES ('" +
        nome + "', '" + descricao + "', " + str(preco) + ", " + str(estoque) + ", '" + categoria + "')"
    )
    return cursor.lastrowid

def atualizar_produto(id, nome, descricao, preco, estoque, categoria):
    executar(
        "UPDATE produtos SET nome = '" + nome + "', descricao = '" + descricao +
        "', preco = " + str(preco) + ", estoque = " + str(estoque) +
        ", categoria = '" + categoria + "' WHERE id = " + str(id)
    )
    return True

def deletar_produto(id):
    executar("DELETE FROM produtos WHERE id = " + str(id))
    return True

def get_todos_usuarios():
    rows = buscar_todos("SELECT * FROM usuarios")
    return [map_usuario(row) for row in rows]

def get_usuario_por_id(id):
    row = buscar_um("SELECT * FROM usuarios WHERE id = " + str(id))
    if row:
        return map_usuario(row)
    return None

def login_usuario(email, senha):
    row = buscar_um(
        "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
    )
    if row:
        return map_usuario_publico(row)
    return None

def criar_usuario(nome, email, senha, tipo="cliente"):
    cursor = executar(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
        nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
    )
    return cursor.lastrowid

def criar_pedido(usuario_id, itens):
    db = get_db()
    cursor = db.cursor()

    total = 0

    for item in itens:
        cursor.execute("SELECT * FROM produtos WHERE id = " + str(item["produto_id"]))
        produto = cursor.fetchone()
        if produto is None:
            return {"erro": "Produto " + str(item["produto_id"]) + " não encontrado"}
        if produto["estoque"] < item["quantidade"]:
            return {"erro": "Estoque insuficiente para " + produto["nome"]}
        total = total + (produto["preco"] * item["quantidade"])

    cursor.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (" +
        str(usuario_id) + ", 'pendente', " + str(total) + ")"
    )
    pedido_id = cursor.lastrowid

    for item in itens:
        cursor.execute("SELECT preco FROM produtos WHERE id = " + str(item["produto_id"]))
        produto = cursor.fetchone()
        cursor.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (" +
            str(pedido_id) + ", " + str(item["produto_id"]) + ", " +
            str(item["quantidade"]) + ", " + str(produto["preco"]) + ")"
        )

        cursor.execute(
            "UPDATE produtos SET estoque = estoque - " + str(item["quantidade"]) +
            " WHERE id = " + str(item["produto_id"])
        )

    db.commit()
    return {"pedido_id": pedido_id, "total": total}

def get_pedidos_usuario(usuario_id):
    rows = buscar_todos("SELECT * FROM pedidos WHERE usuario_id = " + str(usuario_id))
    return montar_pedidos(rows)

def get_todos_pedidos():
    rows = buscar_todos("SELECT * FROM pedidos")
    return montar_pedidos(rows)

def relatorio_vendas():
    total_pedidos = contar("SELECT COUNT(*) FROM pedidos")

    faturamento = buscar_um("SELECT SUM(total) FROM pedidos")[0]
    if faturamento is None:
        faturamento = 0

    pendentes = contar("SELECT COUNT(*) FROM pedidos WHERE status = 'pendente'")
    aprovados = contar("SELECT COUNT(*) FROM pedidos WHERE status = 'aprovado'")
    cancelados = contar("SELECT COUNT(*) FROM pedidos WHERE status = 'cancelado'")

    desconto = 0
    if faturamento > 10000:
        desconto = faturamento * 0.1
    elif faturamento > 5000:
        desconto = faturamento * 0.05
    elif faturamento > 1000:
        desconto = faturamento * 0.02

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": pendentes,
        "pedidos_aprovados": aprovados,
        "pedidos_cancelados": cancelados,
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0
    }

def atualizar_status_pedido(pedido_id, novo_status):
    executar(
        "UPDATE pedidos SET status = '" + novo_status + "' WHERE id = " + str(pedido_id)
    )
    return True

def buscar_produtos(termo, categoria=None, preco_min=None, preco_max=None):
    query = "SELECT * FROM produtos WHERE 1=1"
    if termo:
        query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
    if categoria:
        query += " AND categoria = '" + categoria + "'"
    if preco_min:
        query += " AND preco >= " + str(preco_min)
    if preco_max:
        query += " AND preco <= " + str(preco_max)

    rows = buscar_todos(query)
    return [map_produto(row) for row in rows]
