"""Helpers compartilhados de resposta HTTP, tratamento de erros e validação."""
from functools import wraps
from flask import jsonify

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
STATUS_PEDIDO_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
NOME_MIN = 2
NOME_MAX = 200


def sucesso(dados=None, mensagem=None, status=200, **extra):
    corpo = {}
    if dados is not None:
        corpo["dados"] = dados
    corpo["sucesso"] = True
    if mensagem is not None:
        corpo["mensagem"] = mensagem
    corpo.update(extra)
    return jsonify(corpo), status


def erro(mensagem, status=400, **extra):
    corpo = {"erro": mensagem}
    corpo.update(extra)
    return jsonify(corpo), status


def tratar_erros(prefixo_log=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if prefixo_log:
                    print(prefixo_log + str(e))
                return erro(str(e), 500)
        return wrapper
    return decorator


def extrair_campos_produto(dados):
    """Valida os campos comuns de produto e devolve (campos, mensagem_de_erro)."""
    if not dados:
        return None, "Dados inválidos"
    for campo, mensagem in (("nome", "Nome é obrigatório"),
                            ("preco", "Preço é obrigatório"),
                            ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            return None, mensagem

    campos = {
        "nome": dados["nome"],
        "descricao": dados.get("descricao", ""),
        "preco": dados["preco"],
        "estoque": dados["estoque"],
        "categoria": dados.get("categoria", "geral"),
    }

    if campos["preco"] < 0:
        return None, "Preço não pode ser negativo"
    if campos["estoque"] < 0:
        return None, "Estoque não pode ser negativo"

    return campos, None
