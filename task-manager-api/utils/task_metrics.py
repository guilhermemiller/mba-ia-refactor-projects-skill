"""Métricas de tasks compartilhadas entre rotas de tasks e de relatórios."""
from datetime import datetime

from utils.helpers import VALID_STATUSES


def count_by_status(tasks):
    counts = {status: 0 for status in VALID_STATUSES}
    for task in tasks:
        if task.status in counts:
            counts[task.status] = counts[task.status] + 1
    return counts


def count_overdue(tasks):
    return sum(1 for task in tasks if task.is_overdue())


def overdue_details(tasks):
    result = []
    for task in tasks:
        if task.is_overdue():
            result.append({
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'days_overdue': (datetime.utcnow() - task.due_date).days
            })
    return result
