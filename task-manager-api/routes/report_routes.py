from flask import Blueprint, jsonify
from database import db
from models.task import Task
from models.user import User
from models.category import Category
from datetime import datetime, timedelta
from utils.helpers import calculate_percentage
from utils.responses import commit_or_error, error_response, get_or_error, json_body
from utils.task_metrics import count_by_status, count_overdue, overdue_details

report_bp = Blueprint('reports', __name__)

@report_bp.route('/reports/summary', methods=['GET'])
def summary_report():
    all_tasks = Task.query.all()
    status_counts = count_by_status(all_tasks)
    overdue_list = overdue_details(all_tasks)

    priority_counts = {p: 0 for p in range(1, 6)}
    for t in all_tasks:
        if t.priority in priority_counts:
            priority_counts[t.priority] = priority_counts[t.priority] + 1

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_tasks = Task.query.filter(Task.created_at >= seven_days_ago).count()
    recent_done = Task.query.filter(
        Task.status == 'done',
        Task.updated_at >= seven_days_ago
    ).count()

    user_stats = []
    for u in User.query.all():
        user_tasks = Task.query.filter_by(user_id=u.id).all()
        completed = count_by_status(user_tasks)['done']
        user_stats.append({
            'user_id': u.id,
            'user_name': u.name,
            'total_tasks': len(user_tasks),
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, len(user_tasks))
        })

    report = {
        'generated_at': str(datetime.utcnow()),
        'overview': {
            'total_tasks': len(all_tasks),
            'total_users': User.query.count(),
            'total_categories': Category.query.count(),
        },
        'tasks_by_status': {
            'pending': status_counts['pending'],
            'in_progress': status_counts['in_progress'],
            'done': status_counts['done'],
            'cancelled': status_counts['cancelled'],
        },
        'tasks_by_priority': {
            'critical': priority_counts[1],
            'high': priority_counts[2],
            'medium': priority_counts[3],
            'low': priority_counts[4],
            'minimal': priority_counts[5],
        },
        'overdue': {
            'count': len(overdue_list),
            'tasks': overdue_list,
        },
        'recent_activity': {
            'tasks_created_last_7_days': recent_tasks,
            'tasks_completed_last_7_days': recent_done,
        },
        'user_productivity': user_stats,
    }

    return jsonify(report), 200

@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
def user_report(user_id):
    user, err = get_or_error(User, user_id, 'Usuário não encontrado')
    if err:
        return err

    tasks = Task.query.filter_by(user_id=user_id).all()
    status_counts = count_by_status(tasks)
    high_priority = sum(1 for t in tasks if t.priority <= 2)

    report = {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
        },
        'statistics': {
            'total_tasks': len(tasks),
            'done': status_counts['done'],
            'pending': status_counts['pending'],
            'in_progress': status_counts['in_progress'],
            'cancelled': status_counts['cancelled'],
            'overdue': count_overdue(tasks),
            'high_priority': high_priority,
            'completion_rate': calculate_percentage(status_counts['done'], len(tasks))
        }
    }

    return jsonify(report), 200

@report_bp.route('/categories', methods=['GET'])
def get_categories():
    result = []
    for c in Category.query.all():
        cat_data = c.to_dict()
        cat_data['task_count'] = Task.query.filter_by(category_id=c.id).count()
        result.append(cat_data)
    return jsonify(result), 200

@report_bp.route('/categories', methods=['POST'])
def create_category():
    data, err = json_body()
    if err:
        return err

    name = data.get('name')
    if not name:
        return error_response('Nome é obrigatório')

    category = Category()
    category.name = name
    category.description = data.get('description', '')
    category.color = data.get('color', '#000000')

    db.session.add(category)
    err = commit_or_error('Erro ao criar categoria')
    if err:
        return err

    return jsonify(category.to_dict()), 201

@report_bp.route('/categories/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    cat, err = get_or_error(Category, cat_id, 'Categoria não encontrada')
    if err:
        return err

    data, err = json_body()
    if err:
        return err

    if 'name' in data:
        cat.name = data['name']
    if 'description' in data:
        cat.description = data['description']
    if 'color' in data:
        cat.color = data['color']

    err = commit_or_error('Erro ao atualizar')
    if err:
        return err

    return jsonify(cat.to_dict()), 200

@report_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    cat, err = get_or_error(Category, cat_id, 'Categoria não encontrada')
    if err:
        return err

    db.session.delete(cat)
    err = commit_or_error('Erro ao deletar')
    if err:
        return err

    return jsonify({'message': 'Categoria deletada'}), 200
