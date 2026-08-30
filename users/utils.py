from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def create_password_reset_credentials(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def build_password_reset_url(uid, token):
    return (
        f"{settings.FRONTEND_URL}/pages/auth/confirm_password.html"
        f"?uid={uid}&token={token}"
    )


def send_password_reset_email(user, uid, token):
    reset_url = build_password_reset_url(uid, token)
    context = {"reset_url": reset_url}
    email = create_password_reset_email(user.email, context)
    email.send()


def create_password_reset_email(recipient, context):
    text_body = render_to_string("emails/password_reset_email.txt", context)
    html_body = render_to_string("emails/password_reset_email.html", context)
    email = EmailMultiAlternatives(
        subject="Reset your password",
        body=text_body,
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    return email


def blacklist_refresh_token(token):
    refresh = RefreshToken(token)
    refresh.blacklist()


def delete_auth_cookies(response):
    response.delete_cookie(settings.JWT_ACCESS_COOKIE)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE)


def create_access_token(refresh_token):
    refresh = RefreshToken(refresh_token)
    return str(refresh.access_token)


def create_jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_access_cookie(response, access_token):
    _set_access_cookie(response, access_token)


def set_auth_cookies(response, access_token, refresh_token):
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)


def _set_access_cookie(response, token):
    max_age = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=int(max_age),
    )


def _set_refresh_cookie(response, token):
    max_age = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=int(max_age),
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


def get_user_from_uid(uidb64):
    user_model = get_user_model()
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return user_model.objects.get(pk=user_id)
    except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
        return None


def is_valid_user_token(user, token):
    return bool(user and default_token_generator.check_token(user, token))


def get_active_user_by_email(email):
    user_model = get_user_model()
    return user_model.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()


def authenticate_user(email, password):
    return authenticate(
        username=email.strip().lower(),
        password=password,
    )


def activate_user(user):
    user.is_active = True
    user.save(update_fields=["is_active"])


def update_user_password(user, new_password):
    user.set_password(new_password)
    user.save(update_fields=["password"])


def try_blacklist_refresh_token(token):
    try:
        blacklist_refresh_token(token)
        return True
    except TokenError:
        return False


def try_create_access_token(token):
    try:
        return create_access_token(token)
    except TokenError:
        return None
