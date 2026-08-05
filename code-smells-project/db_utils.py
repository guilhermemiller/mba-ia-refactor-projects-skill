"""Helpers compartilhados de acesso ao banco e de mapeamento de linhas."""
from database import get_db


def buscar_todos(sql):
    cursor = get_db().cursor()
    cursor.execute(sql)
    return cursor.fetchall()


def buscar_um(sql):
    cursor = get_db().cursor()
    cursor.execute(sql)
    return cursor.fetchone()


def contar(sql):
    return buscar_um(sql)[0]


def executar(sql):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    return cursor


def map_produto(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"]
    }


def map_usuario(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "senha": row["senha"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"]
    }


def map_usuario_publico(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"]
    }


def map_pedido(row):
    return {
        "id": row["id"],
        "usuario_id": row["usuario_id"],
        "status": row["status"],
        "total": row["total"],
        "criado_em": row["criado_em"],
        "itens": []
    }


def map_itens_pedido(pedido_id):
    itens = buscar_todos("SELECT * FROM itens_pedido WHERE pedido_id = " + str(pedido_id))
    result = []
    for item in itens:
        prod = buscar_um("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
        result.append({
            "produto_id": item["produto_id"],
            "produto_nome": prod["nome"] if prod else "Desconhecido",
            "quantidade": item["quantidade"],
            "preco_unitario": item["preco_unitario"]
        })
    return result


def montar_pedidos(rows):
    pedidos = []
    for row in rows:
        pedido = map_pedido(row)
        pedido["itens"] = map_itens_pedido(row["id"])
        pedidos.append(pedido)
    return pedidos
