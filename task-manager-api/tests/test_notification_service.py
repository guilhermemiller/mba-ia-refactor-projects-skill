from types import SimpleNamespace

import pytest

from services.notification_service import NotificationService


class FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_args = None
        self.sent = []
        self.quit_called = False
        FakeSMTP.instances.append(self)

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.login_args = (user, password)

    def sendmail(self, sender, to, message):
        self.sent.append((sender, to, message))

    def quit(self):
        self.quit_called = True


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr('services.notification_service.smtplib.SMTP', FakeSMTP)
    return FakeSMTP


@pytest.fixture
def service():
    return NotificationService()


def make_user(user_id=1, name='Alice', email='alice@example.com'):
    return SimpleNamespace(id=user_id, name=name, email=email)


def make_task(task_id=10, title='Write tests', priority=2, status='pending', due_date='2024-05-01'):
    return SimpleNamespace(id=task_id, title=title, priority=priority, status=status, due_date=due_date)


def test_send_email_uses_configured_smtp_server(service, smtp):
    assert service.send_email('to@example.com', 'Subject', 'Body') is True

    server = smtp.instances[0]
    assert (server.host, server.port) == ('smtp.gmail.com', 587)
    assert server.started_tls is True
    assert server.login_args == ('taskmanager@gmail.com', 'senha123')
    assert server.sent == [('taskmanager@gmail.com', 'to@example.com', 'Subject: Subject\n\nBody')]
    assert server.quit_called is True


def test_send_email_returns_false_when_smtp_fails(service, monkeypatch, capsys):
    def explode(host, port):
        raise OSError('connection refused')

    monkeypatch.setattr('services.notification_service.smtplib.SMTP', explode)

    assert service.send_email('to@example.com', 'Subject', 'Body') is False
    assert 'Erro ao enviar email: connection refused' in capsys.readouterr().out


def test_notify_task_assigned_sends_email_and_records_notification(service, smtp):
    user = make_user()
    task = make_task()

    service.notify_task_assigned(user, task)

    _, to, message = smtp.instances[0].sent[0]
    assert to == user.email
    assert 'Subject: Nova task atribuída: Write tests' in message
    assert 'Prioridade: 2' in message
    assert 'Status: pending' in message

    assert len(service.notifications) == 1
    notification = service.notifications[0]
    assert notification['type'] == 'task_assigned'
    assert notification['user_id'] == user.id
    assert notification['task_id'] == task.id
    assert notification['timestamp'] is not None


def test_notify_task_overdue_sends_email_without_recording(service, smtp):
    service.notify_task_overdue(make_user(), make_task())

    _, _, message = smtp.instances[0].sent[0]
    assert 'Subject: Task atrasada: Write tests' in message
    assert 'Data limite: 2024-05-01' in message
    assert service.notifications == []


def test_get_notifications_filters_by_user(service, smtp):
    service.notify_task_assigned(make_user(user_id=1), make_task(task_id=1))
    service.notify_task_assigned(make_user(user_id=2), make_task(task_id=2))

    result = service.get_notifications(1)

    assert [n['task_id'] for n in result] == [1]
    assert service.get_notifications(99) == []
