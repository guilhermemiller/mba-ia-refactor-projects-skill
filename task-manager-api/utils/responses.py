"""Helpers compartilhados de resposta HTTP e de persistência."""
from flask import jsonify, request
from database import db


def error_response(message, status=400):
    return jsonify({'error': message}), status


def json_body():
    """Devolve (dados, resposta_de_erro) para o corpo JSON da requisição."""
    data = request.get_json(silent=True)
    if not data:
        return None, error_response('Dados inválidos', 400)
    return data, None


def get_or_error(model, obj_id, message):
    """Busca um registro por id e devolve (registro, resposta_de_erro)."""
    obj = model.query.get(obj_id)
    if not obj:
        return None, error_response(message, 404)
    return obj, None


def commit_or_error(message, log_error=None):
    """Efetiva a sessão e devolve uma resposta de erro em caso de falha."""
    try:
        db.session.commit()
        return None
    except Exception as e:
        db.session.rollback()
        if log_error:
            print(f"{log_error}: {str(e)}")
        return error_response(message, 500)
