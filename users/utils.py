"""Authentication, token, cookie, and email helper functions used by user views."""

from email.message import MIMEPart

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
    """Create a URL-safe user ID and time-limited password-reset token."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def build_password_reset_url(uid, token):
    """Build the frontend URL that receives password-reset credentials."""
    return (
        f"{settings.FRONTEND_URL}/pages/auth/confirm_password.html"
        f"?uid={uid}&token={token}"
    )


def send_password_reset_email(user, uid, token):
    """Render and send the password-reset email to the user."""
    reset_url = build_password_reset_url(uid, token)
    context = {"reset_url": reset_url}
    email = create_password_reset_email(user.email, context)
    email.send()


def create_password_reset_email(recipient, context):
    """Create a multipart plain-text and HTML password-reset email."""
    text_body = render_to_string("emails/password_reset_email.txt", context)
    html_body = render_to_string("emails/password_reset_email.html", context)
    email = EmailMultiAlternatives(
        subject="Reset your password",
        body=text_body,
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    attach_inline_logo(email)
    return email


def attach_inline_logo(email):
    """Embed the Videoflix logo as a Django 6 compatible MIME part."""
    logo_path = settings.BASE_DIR / "users/static/users/images/videoflix_logo.png"
    logo = MIMEPart()
    logo.set_content(
        logo_path.read_bytes(),
        maintype="image",
        subtype="png",
        disposition="inline",
        cid="<videoflix-logo>",
        filename="videoflix_logo.png",
    )
    email.attach(logo)


def blacklist_refresh_token(token):
    """Invalidate a refresh token through Simple JWT's blacklist."""
    refresh = RefreshToken(token)
    refresh.blacklist()


def delete_auth_cookies(response):
    """Remove access and refresh authentication cookies from a response."""
    response.delete_cookie(settings.JWT_ACCESS_COOKIE)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE)


def create_access_token(refresh_token):
    """Create a fresh access token from a valid refresh token."""
    refresh = RefreshToken(refresh_token)
    return str(refresh.access_token)


def create_jwt_tokens(user):
    """Create a new access/refresh token pair for an authenticated user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_access_cookie(response, access_token):
    """Store a renewed access token in the configured HttpOnly cookie."""
    _set_access_cookie(response, access_token)


def set_auth_cookies(response, access_token, refresh_token):
    """Store access and refresh tokens in configured HttpOnly cookies."""
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)


def _set_access_cookie(response, token):
    """Set the access cookie with security flags and matching token lifetime."""
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
    """Set the refresh cookie with security flags and matching token lifetime."""
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
    """Create the URL-safe user ID and token used for account activation."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token


def build_activation_url(uid, token):
    """Build the frontend URL that receives account-activation credentials."""
    return f"{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uid}&token={token}"


def send_activation_email(user, uid, token):
    """Render and send the account-activation email to the new user."""
    activation_url = build_activation_url(uid, token)
    context = {"activation_url": activation_url}
    email = create_activation_email(user.email, context)
    email.send()


def create_activation_email(recipient, context):
    """Create a multipart plain-text and HTML account-activation email."""
    text_body = render_to_string("emails/activation_email.txt", context)
    html_body = render_to_string("emails/activation_email.html", context)

    email = EmailMultiAlternatives(
        subject="Confirm your email",
        body=text_body,
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    attach_inline_logo(email)
    return email


def get_user_from_uid(uidb64):
    """Decode a URL-safe user ID and return the matching user when available."""
    user_model = get_user_model()
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        return user_model.objects.get(pk=user_id)
    except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
        return None


def is_valid_user_token(user, token):
    """Check whether a user exists and the supplied Django token is valid."""
    return bool(user and default_token_generator.check_token(user, token))


def get_active_user_by_email(email):
    """Return the active account matching an email address, if one exists."""
    user_model = get_user_model()
    return user_model.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()


def authenticate_user(email, password):
    """Authenticate normalized email/password credentials through Django."""
    return authenticate(
        username=email.strip().lower(),
        password=password,
    )


def activate_user(user):
    """Mark a successfully verified account as active."""
    user.is_active = True
    user.save(update_fields=["is_active"])


def update_user_password(user, new_password):
    """Hash and persist a user's replacement password."""
    user.set_password(new_password)
    user.save(update_fields=["password"])


def try_blacklist_refresh_token(token):
    """Blacklist a refresh token and report whether invalidation succeeded."""
    try:
        blacklist_refresh_token(token)
        return True
    except TokenError:
        return False


def try_create_access_token(token):
    """Return a new access token or None when the refresh token is invalid."""
    try:
        return create_access_token(token)
    except TokenError:
        return None
