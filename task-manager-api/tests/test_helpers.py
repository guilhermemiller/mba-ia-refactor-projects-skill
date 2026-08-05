from datetime import datetime

import pytest

from utils import helpers


def test_format_date_returns_string_for_datetime():
    assert helpers.format_date(datetime(2024, 5, 1)) == '2024-05-01 00:00:00'


def test_format_date_returns_none_for_falsy_value():
    assert helpers.format_date(None) is None


@pytest.mark.parametrize('part, total, expected', [
    (1, 4, 25.0),
    (1, 3, 33.33),
    (0, 5, 0.0),
    (5, 0, 0),
])
def test_calculate_percentage(part, total, expected):
    assert helpers.calculate_percentage(part, total) == expected


@pytest.mark.parametrize('email, expected', [
    ('user@example.com', True),
    ('user+tag@sub.example.com', True),
    ('user_name.surname@example', True),
    ('no-at-sign', False),
    ('@example.com', False),
])
def test_validate_email(email, expected):
    assert helpers.validate_email(email) is expected


@pytest.mark.parametrize('value, expected', [
    ('  padded  ', 'padded'),
    ('', ''),
    (None, None),
])
def test_sanitize_string(value, expected):
    assert helpers.sanitize_string(value) == expected


def test_generate_id_returns_unique_uuid_strings():
    first = helpers.generate_id()
    second = helpers.generate_id()

    assert len(first) == 36
    assert first != second


def test_log_action_prints_action_only(capsys):
    helpers.log_action('created')

    out = capsys.readouterr().out
    assert 'ACTION: created' in out
    assert 'DETAILS' not in out


def test_log_action_prints_details_when_given(capsys):
    helpers.log_action('created', details={'id': 1})

    out = capsys.readouterr().out
    assert "DETAILS: {'id': 1}" in out


@pytest.mark.parametrize('value, expected', [
    ('2024-05-01', datetime(2024, 5, 1)),
    ('01/05/2024', datetime(2024, 5, 1)),
    ('not-a-date', None),
    ('', None),
])
def test_parse_date(value, expected):
    assert helpers.parse_date(value) == expected


@pytest.mark.parametrize('color, expected', [
    ('#ffffff', True),
    ('ffffff', False),
    ('#fff', False),
    ('', False),
    (None, False),
])
def test_is_valid_color(color, expected):
    assert helpers.is_valid_color(color) is expected


def test_process_task_data_accepts_full_payload():
    data = {
        'title': '  Buy milk  ',
        'description': 'from the market',
        'status': 'in_progress',
        'priority': '4',
        'due_date': '2024-05-01',
        'tags': ['home', 'errand'],
    }

    result, error = helpers.process_task_data(data)

    assert error is None
    assert result == {
        'title': 'Buy milk',
        'description': 'from the market',
        'status': 'in_progress',
        'priority': 4,
        'due_date': datetime(2024, 5, 1),
        'tags': 'home,errand',
    }


def test_process_task_data_ignores_absent_fields():
    result, error = helpers.process_task_data({})

    assert (result, error) == ({}, None)


def test_process_task_data_keeps_string_tags_as_is():
    result, _ = helpers.process_task_data({'tags': 'home,errand'})

    assert result['tags'] == 'home,errand'


def test_process_task_data_allows_clearing_due_date():
    result, error = helpers.process_task_data({'due_date': None})

    assert error is None
    assert result['due_date'] is None


@pytest.mark.parametrize('data, expected_error', [
    ({'title': 'ab'}, 'Título deve ter entre 3 e 200 caracteres'),
    ({'title': 'a' * 201}, 'Título deve ter entre 3 e 200 caracteres'),
    ({'title': ''}, 'Título não pode ser vazio'),
    ({'status': 'archived'}, 'Status inválido'),
    ({'priority': 0}, 'Prioridade deve ser entre 1 e 5'),
    ({'priority': 6}, 'Prioridade deve ser entre 1 e 5'),
    ({'priority': 'high'}, 'Prioridade inválida'),
    ({'due_date': '31-31-2024'}, 'Data inválida'),
])
def test_process_task_data_rejects_invalid_values(data, expected_error):
    result, error = helpers.process_task_data(data)

    assert result is None
    assert error == expected_error


def test_module_constants_match_route_validation_rules():
    assert helpers.VALID_STATUSES == ['pending', 'in_progress', 'done', 'cancelled']
    assert helpers.VALID_ROLES == ['user', 'admin', 'manager']
    assert (helpers.MIN_TITLE_LENGTH, helpers.MAX_TITLE_LENGTH) == (3, 200)
    assert helpers.MIN_PASSWORD_LENGTH == 4
    assert helpers.DEFAULT_PRIORITY == 3
    assert helpers.DEFAULT_COLOR == '#000000'
