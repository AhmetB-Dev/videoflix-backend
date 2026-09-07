"""Background tasks for account-related email delivery."""

import django_rq
from django.contrib.auth import get_user_model
from django.db import transaction

from .utils import create_activation_credentials, send_activation_email


def send_activation_email_task(user_id):
    """Send a fresh activation email when the account is still inactive."""
    user_model = get_user_model()
    user = user_model.objects.filter(pk=user_id, is_active=False).first()
    if user is None:
        return

    uid, token = create_activation_credentials(user)
    send_activation_email(user, uid, token)


def schedule_activation_email(user):
    """Enqueue activation email delivery only after the user commit succeeds."""
    user_id = user.pk
    transaction.on_commit(
        lambda: django_rq.enqueue(send_activation_email_task, user_id),
        robust=True,
    )
