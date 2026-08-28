from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def create_activation_credentials(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def build_activation_url(uid, token):
    return f"{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uid}&token={token}"


def send_activation_email(user, uid, token):
    activation_url = build_activation_url(uid, token)
    context = {"activation_url": activation_url}
    email = create_activation_email(user.email, context)
    email.send()


def create_activation_email(recipient, context):
    text_body = render_to_string("emails/activation_email.txt", context)
    html_body = render_to_string("emails/activation_email.html", context)
    email = EmailMultiAlternatives(
        subject="Confirm your email",
        body=text_body,
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    return email
