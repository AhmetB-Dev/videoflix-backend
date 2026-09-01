"""Custom JWT authentication that reads access tokens from HttpOnly cookies."""

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate API requests with the JWT access token stored in an HttpOnly cookie.

    This keeps authentication tokens out of JavaScript-accessible storage while
    remaining compatible with Simple JWT token validation."""

    def authenticate(self, request):
        """Read, validate, and resolve the user from the access-token cookie."""
        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        return user, validated_token
