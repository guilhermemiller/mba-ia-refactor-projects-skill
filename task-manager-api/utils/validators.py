"""Validações compartilhadas entre as rotas.

Cada função devolve a mensagem de erro ou None quando o valor é válido.
"""
import re
from datetime import datetime

from utils.helpers import (
    MAX_TITLE_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_TITLE_LENGTH,
    VALID_ROLES,
    VALID_STATUSES,
)

EMAIL_REGEX = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DATE_FORMAT = '%Y-%m-%d'


def validate_title_length(title):
    if len(title) < MIN_TITLE_LENGTH:
        return 'Título muito curto'
    if len(title) > MAX_TITLE_LENGTH:
        return 'Título muito longo'
    return None


def validate_status(status):
    if status not in VALID_STATUSES:
        return 'Status inválido'
    return None


def validate_priority(priority):
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        return f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}'
    return None


def validate_role(role):
    if role not in VALID_ROLES:
        return 'Role inválido'
    return None


def validate_email(email):
    if not re.match(EMAIL_REGEX, email):
        return 'Email inválido'
    return None


def validate_password(password, message='Senha muito curta'):
    if len(password) < MIN_PASSWORD_LENGTH:
        return message
    return None


def parse_due_date(value, message='Formato de data inválido'):
    """Devolve (data, mensagem_de_erro) para uma data no formato YYYY-MM-DD."""
    try:
        return datetime.strptime(value, DATE_FORMAT), None
    except (ValueError, TypeError):
        return None, message


def normalize_tags(tags):
    if isinstance(tags, list):
        return ','.join(tags)
    return tags
