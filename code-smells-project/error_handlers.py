import logging

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({"erro": error.description, "sucesso": False}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        logger.exception("Erro não tratado em %s %s", request.method, request.path)
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
