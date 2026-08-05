import logging

from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from database import db

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({'error': error.description}), error.code

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        db.session.rollback()
        logger.exception('Erro de banco em %s %s', request.method, request.path)
        return jsonify({'error': 'Erro ao acessar o banco de dados'}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        db.session.rollback()
        logger.exception('Erro não tratado em %s %s', request.method, request.path)
        return jsonify({'error': 'Erro interno'}), 500
