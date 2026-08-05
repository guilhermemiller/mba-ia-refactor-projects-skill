import logging
import smtplib
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Falha ao entregar um email de notificação."""


class NotificationService:
    def __init__(self):
        self.notifications = []
        self.email_host = 'smtp.gmail.com'
        self.email_port = 587
        self.email_user = 'taskmanager@gmail.com'
        self.email_password = 'senha123'

    def send_email(self, to, subject, body):
        try:
            server = smtplib.SMTP(self.email_host, self.email_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(self.email_user, to, message)
            server.quit()
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError(f'Falha ao enviar email para {to}') from error

        logger.info('Email enviado para %s', to)

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\nPrioridade: {task.priority}\nStatus: {task.status}"
        delivered = self._deliver(user.email, subject, body)
        self.notifications.append({
            'type': 'task_assigned',
            'user_id': user.id,
            'task_id': task.id,
            'timestamp': datetime.utcnow(),
            'delivered': delivered
        })
        return delivered

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        return self._deliver(user.email, subject, body)

    def _deliver(self, to, subject, body):
        try:
            self.send_email(to, subject, body)
        except EmailDeliveryError:
            logger.exception('Notificação não entregue para %s', to)
            return False
        return True

    def get_notifications(self, user_id):
        result = []
        for n in self.notifications:
            if n['user_id'] == user_id:
                result.append(n)
        return result
