from flask import request, jsonify
import models
from database import get_db
from api_utils import (
    CATEGORIAS_VALIDAS,
    NOME_MAX,
    NOME_MIN,
    STATUS_PEDIDO_VALIDOS,
    erro,
    extrair_campos_produto,
    sucesso,
    tratar_erros,
)

@tratar_erros("ERRO: ")
def listar_produtos():
    produtos = models.get_todos_produtos()
    print("Listando " + str(len(produtos)) + " produtos")
    return sucesso(produtos)

@tratar_erros()
def buscar_produto(id):
    produto = models.get_produto_por_id(id)
    if produto:
        return sucesso(produto)
    return erro("Produto não encontrado", 404, sucesso=False)

@tratar_erros("ERRO ao criar produto: ")
def criar_produto():
    dados = request.get_json()

    campos, mensagem = extrair_campos_produto(dados)
    if mensagem:
        return erro(mensagem)

    if len(campos["nome"]) < NOME_MIN:
        return erro("Nome muito curto")
    if len(campos["nome"]) > NOME_MAX:
        return erro("Nome muito longo")
    if campos["categoria"] not in CATEGORIAS_VALIDAS:
        return erro("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    id = models.criar_produto(campos["nome"], campos["descricao"], campos["preco"],
                              campos["estoque"], campos["categoria"])
    print("Produto criado com ID: " + str(id))
    return sucesso({"id": id}, mensagem="Produto criado", status=201)

@tratar_erros()
def atualizar_produto(id):
    dados = request.get_json()

    produto_existente = models.get_produto_por_id(id)
    if not produto_existente:
        return erro("Produto não encontrado", 404)

    campos, mensagem = extrair_campos_produto(dados)
    if mensagem:
        return erro(mensagem)

    models.atualizar_produto(id, campos["nome"], campos["descricao"], campos["preco"],
                             campos["estoque"], campos["categoria"])
    return sucesso(mensagem="Produto atualizado")

@tratar_erros()
def deletar_produto(id):
    produto = models.get_produto_por_id(id)
    if not produto:
        return erro("Produto não encontrado", 404)

    models.deletar_produto(id)
    print("Produto " + str(id) + " deletado")
    return sucesso(mensagem="Produto deletado")

@tratar_erros()
def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    if preco_min:
        preco_min = float(preco_min)
    if preco_max:
        preco_max = float(preco_max)

    resultados = models.buscar_produtos(termo, categoria, preco_min, preco_max)
    return sucesso(resultados, total=len(resultados))

@tratar_erros()
def listar_usuarios():
    return sucesso(models.get_todos_usuarios())

@tratar_erros()
def buscar_usuario(id):
    usuario = models.get_usuario_por_id(id)
    if usuario:
        return sucesso(usuario)
    return erro("Usuário não encontrado", 404)

@tratar_erros()
def criar_usuario():
    dados = request.get_json()

    if not dados:
        return erro("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        return erro("Nome, email e senha são obrigatórios")

    id = models.criar_usuario(nome, email, senha)
    print("Usuário criado: " + email)
    return sucesso({"id": id}, status=201)

@tratar_erros()
def login():
    dados = request.get_json()
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        return erro("Email e senha são obrigatórios")

    usuario = models.login_usuario(email, senha)
    if usuario:
        print("Login bem-sucedido: " + email)
        return sucesso(usuario, mensagem="Login OK")

    print("Login falhou: " + email)
    return erro("Email ou senha inválidos", 401, sucesso=False)

@tratar_erros("ERRO CRITICO ao criar pedido: ")
def criar_pedido():
    dados = request.get_json()

    if not dados:
        return erro("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        return erro("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        return erro("Pedido deve ter pelo menos 1 item")

    resultado = models.criar_pedido(usuario_id, itens)

    if "erro" in resultado:
        return erro(resultado["erro"], 400, sucesso=False)

    print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado para usuario " + str(usuario_id))
    print("ENVIANDO SMS: Seu pedido foi recebido!")
    print("ENVIANDO PUSH: Novo pedido recebido pelo sistema")

    return sucesso(resultado, mensagem="Pedido criado com sucesso", status=201)

@tratar_erros()
def listar_pedidos_usuario(usuario_id):
    return sucesso(models.get_pedidos_usuario(usuario_id))

@tratar_erros()
def listar_todos_pedidos():
    return sucesso(models.get_todos_pedidos())

@tratar_erros()
def atualizar_status_pedido(pedido_id):
    dados = request.get_json()
    novo_status = dados.get("status", "")

    if novo_status not in STATUS_PEDIDO_VALIDOS:
        return erro("Status inválido")

    models.atualizar_status_pedido(pedido_id, novo_status)

    if novo_status == "aprovado":
        print("NOTIFICAÇÃO: Pedido " + str(pedido_id) + " foi aprovado! Preparar envio.")
    if novo_status == "cancelado":
        print("NOTIFICAÇÃO: Pedido " + str(pedido_id) + " cancelado. Devolver estoque.")

    return sucesso(mensagem="Status atualizado")

@tratar_erros()
def relatorio_vendas():
    return sucesso(models.relatorio_vendas())

def health_check():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.execute("SELECT COUNT(*) FROM produtos")
        produtos = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pedidos")
        pedidos = cursor.fetchone()[0]

        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": produtos,
                "usuarios": usuarios,
                "pedidos": pedidos
            },

            "versao": "1.0.0",
            "ambiente": "producao",
            "db_path": "loja.db",
            "debug": True,
            "secret_key": "minha-chave-super-secreta-123"
        }), 200
    except Exception as e:
        return jsonify({"status": "erro", "detalhes": str(e)}), 500
