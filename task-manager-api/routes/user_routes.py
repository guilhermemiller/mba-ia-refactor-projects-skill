from flask import Blueprint, jsonify
from database import db
from models.user import User
from models.task import Task
from utils.responses import commit_or_error, error_response, get_or_error, json_body
from utils.serializers import serialize_task_summary, serialize_user
from utils.validators import validate_email, validate_password, validate_role

user_bp = Blueprint('users', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    result = [serialize_user(u, task_count=len(u.tasks)) for u in users]
    return jsonify(result), 200

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user, err = get_or_error(User, user_id, 'Usuário não encontrado')
    if err:
        return err

    data = user.to_dict()
    data['tasks'] = [t.to_dict() for t in Task.query.filter_by(user_id=user_id).all()]

    return jsonify(data), 200

@user_bp.route('/users', methods=['POST'])
def create_user():
    data, err = json_body()
    if err:
        return err

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')

    if not name:
        return error_response('Nome é obrigatório')
    if not email:
        return error_response('Email é obrigatório')
    if not password:
        return error_response('Senha é obrigatória')

    message = validate_email(email)
    if message:
        return error_response(message)

    message = validate_password(password, 'Senha deve ter no mínimo 4 caracteres')
    if message:
        return error_response(message)

    existing = User.query.filter_by(email=email).first()
    if existing:
        return error_response('Email já cadastrado', 409)

    message = validate_role(role)
    if message:
        return error_response(message)

    user = User()
    user.name = name
    user.email = email
    user.set_password(password)
    user.role = role

    db.session.add(user)
    err = commit_or_error('Erro ao criar usuário', log_error='ERRO')
    if err:
        return err

    print(f"Usuário criado: {user.id} - {user.name}")
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user, err = get_or_error(User, user_id, 'Usuário não encontrado')
    if err:
        return err

    data, err = json_body()
    if err:
        return err

    if 'name' in data:
        user.name = data['name']

    if 'email' in data:
        message = validate_email(data['email'])
        if message:
            return error_response(message)

        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != user_id:
            return error_response('Email já cadastrado', 409)
        user.email = data['email']

    if 'password' in data:
        message = validate_password(data['password'])
        if message:
            return error_response(message)
        user.set_password(data['password'])

    if 'role' in data:
        message = validate_role(data['role'])
        if message:
            return error_response(message)
        user.role = data['role']

    if 'active' in data:
        user.active = data['active']

    err = commit_or_error('Erro ao atualizar')
    if err:
        return err

    return jsonify(user.to_dict()), 200

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user, err = get_or_error(User, user_id, 'Usuário não encontrado')
    if err:
        return err

    for t in Task.query.filter_by(user_id=user_id).all():
        db.session.delete(t)

    db.session.delete(user)
    err = commit_or_error('Erro ao deletar')
    if err:
        return err

    print(f"Usuário deletado: {user_id}")
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200

@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    _, err = get_or_error(User, user_id, 'Usuário não encontrado')
    if err:
        return err

    tasks = Task.query.filter_by(user_id=user_id).all()
    return jsonify([serialize_task_summary(t) for t in tasks]), 200

@user_bp.route('/login', methods=['POST'])
def login():
    data, err = json_body()
    if err:
        return err

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return error_response('Email e senha são obrigatórios')

    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response('Credenciais inválidas', 401)

    if not user.check_password(password):
        return error_response('Credenciais inválidas', 401)

    if not user.active:
        return error_response('Usuário inativo', 403)

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': 'fake-jwt-token-' + str(user.id)
    }), 200
