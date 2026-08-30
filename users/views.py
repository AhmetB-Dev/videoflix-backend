from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
)
from .utils import (
    activate_user,
    authenticate_user,
    create_activation_credentials,
    create_jwt_tokens,
    create_password_reset_credentials,
    delete_auth_cookies,
    get_active_user_by_email,
    get_user_from_uid,
    is_valid_user_token,
    send_activation_email,
    send_password_reset_email,
    set_access_cookie,
    set_auth_cookies,
    try_blacklist_refresh_token,
    try_create_access_token,
    update_user_password,
)

MISSING_REFRESH_TOKEN = {"detail": "Refresh token is missing."}
INVALID_REFRESH_TOKEN = {"detail": "Invalid refresh token."}
INVALID_PASSWORD_TOKEN = {"detail": "Invalid or expired password reset link."}
INVALID_CREDENTIALS = {"detail": "Please check your credentials and try again."}
ACTIVATION_FAILED = {"detail": "Activation failed."}


class PasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        user = get_user_from_uid(uidb64)
        if not is_valid_user_token(user, token):
            return Response(
                INVALID_PASSWORD_TOKEN,
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_user_password(user, serializer.validated_data["new_password"])
        return Response(
            {"detail": "Your Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_active_user_by_email(serializer.validated_data["email"])
        if user:
            uid, token = create_password_reset_credentials(user)
            send_password_reset_email(user, uid, token)
        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not token:
            return Response(MISSING_REFRESH_TOKEN, status=status.HTTP_400_BAD_REQUEST)
        if not try_blacklist_refresh_token(token):
            return Response(INVALID_REFRESH_TOKEN, status=status.HTTP_400_BAD_REQUEST)
        response = Response({"detail": "Logout successful!"})
        delete_auth_cookies(response)
        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if not token:
            return Response(MISSING_REFRESH_TOKEN, status=status.HTTP_400_BAD_REQUEST)
        access_token = try_create_access_token(token)
        if access_token is None:
            return Response(INVALID_REFRESH_TOKEN, status=status.HTTP_401_UNAUTHORIZED)
        response = Response({"detail": "Token refreshed", "access": access_token})
        set_access_cookie(response, access_token)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = authenticate_user(data["email"], data["password"])
        if user is None:
            return Response(
                INVALID_CREDENTIALS,
                status=status.HTTP_401_UNAUTHORIZED,
            )
        access_token, refresh_token = create_jwt_tokens(user)
        response = self._create_response(user)
        set_auth_cookies(response, access_token, refresh_token)
        return response

    @staticmethod
    def _create_response(user):
        data = {
            "detail": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
            },
        }
        return Response(data, status=status.HTTP_200_OK)


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = get_user_from_uid(uidb64)
        if not is_valid_user_token(user, token):
            return Response(
                ACTIVATION_FAILED,
                status=status.HTTP_400_BAD_REQUEST,
            )
        activate_user(user)
        return Response(
            {"message": "Account successfully activated."},
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        uid, token = create_activation_credentials(user)
        send_activation_email(user, uid, token)
        data = {
            "user": {"id": user.id, "email": user.email},
            "token": token,
        }
        return Response(data, status=status.HTTP_201_CREATED)
