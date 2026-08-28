from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken


def create_jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_auth_cookies(response, access_token, refresh_token):
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)


def _set_access_cookie(response, token):
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=30 * 60,
    )


def _set_refresh_cookie(response, token):
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=24 * 60 * 60,
    )


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
