"""Serialização compartilhada dos models expostos pela API."""


def serialize_task(task, include_overdue=False, include_relations=False):
    data = task.to_dict()
    if include_overdue:
        data['overdue'] = task.is_overdue()
    if include_relations:
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
    return data


def serialize_task_summary(task):
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'created_at': str(task.created_at),
        'due_date': str(task.due_date) if task.due_date else None,
        'overdue': task.is_overdue(),
    }


def serialize_user(user, task_count=None):
    data = {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'active': user.active,
        'created_at': str(user.created_at),
    }
    if task_count is not None:
        data['task_count'] = task_count
    return data
