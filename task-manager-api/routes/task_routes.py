from flask import Blueprint, request, jsonify
from database import db
from models.task import Task
from models.user import User
from models.category import Category
from datetime import datetime
from utils.helpers import calculate_percentage
from utils.responses import commit_or_error, error_response, get_or_error, json_body
from utils.serializers import serialize_task
from utils.task_metrics import count_by_status, count_overdue
from utils.validators import (
    normalize_tags,
    parse_due_date,
    validate_priority,
    validate_status,
    validate_title_length,
)

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    try:
        tasks = Task.query.all()
        result = [serialize_task(t, include_overdue=True, include_relations=True) for t in tasks]
        return jsonify(result), 200
    except Exception:
        return error_response('Erro interno', 500)

@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task, err = get_or_error(Task, task_id, 'Task não encontrada')
    if err:
        return err

    return jsonify(serialize_task(task, include_overdue=True)), 200

@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data, err = json_body()
    if err:
        return err

    title = data.get('title')
    if not title:
        return error_response('Título é obrigatório')

    message = validate_title_length(title)
    if message:
        return error_response(message)

    description = data.get('description', '')
    status = data.get('status', 'pending')
    priority = data.get('priority', 3)
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    due_date = data.get('due_date')
    tags = data.get('tags')

    message = validate_status(status) or validate_priority(priority)
    if message:
        return error_response(message)

    if user_id:
        _, err = get_or_error(User, user_id, 'Usuário não encontrado')
        if err:
            return err

    if category_id:
        _, err = get_or_error(Category, category_id, 'Categoria não encontrada')
        if err:
            return err

    task = Task()
    task.title = title
    task.description = description
    task.status = status
    task.priority = priority
    task.user_id = user_id
    task.category_id = category_id

    if due_date:
        parsed, message = parse_due_date(due_date, 'Formato de data inválido. Use YYYY-MM-DD')
        if message:
            return error_response(message)
        task.due_date = parsed

    if tags:
        task.tags = normalize_tags(tags)

    db.session.add(task)
    err = commit_or_error('Erro ao criar task', log_error='Erro ao criar task')
    if err:
        return err

    print(f"Task criada: {task.id} - {task.title}")
    return jsonify(task.to_dict()), 201

@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task, err = get_or_error(Task, task_id, 'Task não encontrada')
    if err:
        return err

    data, err = json_body()
    if err:
        return err

    if 'title' in data:
        message = validate_title_length(data['title'])
        if message:
            return error_response(message)
        task.title = data['title']

    if 'description' in data:
        task.description = data['description']

    if 'status' in data:
        message = validate_status(data['status'])
        if message:
            return error_response(message)
        task.status = data['status']

    if 'priority' in data:
        message = validate_priority(data['priority'])
        if message:
            return error_response(message)
        task.priority = data['priority']

    if 'user_id' in data:
        if data['user_id']:
            _, err = get_or_error(User, data['user_id'], 'Usuário não encontrado')
            if err:
                return err
        task.user_id = data['user_id']

    if 'category_id' in data:
        if data['category_id']:
            _, err = get_or_error(Category, data['category_id'], 'Categoria não encontrada')
            if err:
                return err
        task.category_id = data['category_id']

    if 'due_date' in data:
        if data['due_date']:
            parsed, message = parse_due_date(data['due_date'])
            if message:
                return error_response(message)
            task.due_date = parsed
        else:
            task.due_date = None

    if 'tags' in data:
        task.tags = normalize_tags(data['tags'])

    task.updated_at = datetime.utcnow()

    err = commit_or_error('Erro ao atualizar')
    if err:
        return err

    print(f"Task atualizada: {task.id}")
    return jsonify(task.to_dict()), 200

@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task, err = get_or_error(Task, task_id, 'Task não encontrada')
    if err:
        return err

    db.session.delete(task)
    err = commit_or_error('Erro ao deletar')
    if err:
        return err

    print(f"Task deletada: {task_id}")
    return jsonify({'message': 'Task deletada com sucesso'}), 200

@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks():
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    user_id = request.args.get('user_id', '')

    tasks = Task.query

    if query:
        tasks = tasks.filter(
            db.or_(
                Task.title.like(f'%{query}%'),
                Task.description.like(f'%{query}%')
            )
        )

    if status:
        tasks = tasks.filter(Task.status == status)

    if priority:
        tasks = tasks.filter(Task.priority == int(priority))

    if user_id:
        tasks = tasks.filter(Task.user_id == int(user_id))

    return jsonify([t.to_dict() for t in tasks.all()]), 200

@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    all_tasks = Task.query.all()
    counts = count_by_status(all_tasks)
    total = len(all_tasks)

    stats = {
        'total': total,
        'pending': counts['pending'],
        'in_progress': counts['in_progress'],
        'done': counts['done'],
        'cancelled': counts['cancelled'],
        'overdue': count_overdue(all_tasks),
        'completion_rate': calculate_percentage(counts['done'], total)
    }

    return jsonify(stats), 200
