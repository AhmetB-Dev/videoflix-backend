from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError

from .serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
)
from .utils import (
    create_access_token,
    create_activation_credentials,
    create_jwt_tokens,
    send_activation_email,
    set_access_cookie,
    set_auth_cookies,
    blacklist_refresh_token,
    delete_auth_cookies,
    create_password_reset_credentials,
    send_password_reset_email,
)


class PasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)

        if not self._token_is_valid(user, token):
            return self._invalid_token_response()

        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Your Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_user(uidb64):
        user_model = get_user_model()

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return user_model.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
            return None

    @staticmethod
    def _token_is_valid(user, token):
        return user and default_token_generator.check_token(user, token)

    @staticmethod
    def _invalid_token_response():
        return Response(
            {"detail": "Invalid or expired password reset link."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self._get_user(serializer.validated_data["email"])

        if user:
            uid, token = create_password_reset_credentials(user)
            send_password_reset_email(user, uid, token)

        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_user(email):
        user_model = get_user_model()
        return user_model.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)

        if not token:
            return self._missing_token_response()

        try:
            blacklist_refresh_token(token)
        except TokenError:
            return self._invalid_token_response()

        response = Response(
            {
                "detail": "Logout successful! All tokens will be deleted. "
                "Refresh token is now invalid."
            },
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)
        return response

    @staticmethod
    def _missing_token_response():
        return Response(
            {"detail": "Refresh token is missing."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _invalid_token_response():
        return Response(
            {"detail": "Invalid refresh token."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)

        if not token:
            return self._error("Refresh token is missing.", 400)

        try:
            access_token = create_access_token(token)
        except TokenError:
            return self._error("Invalid refresh token.", 401)

        response = Response(
            {"detail": "Token refreshed", "access": access_token},
            status=status.HTTP_200_OK,
        )
        set_access_cookie(response, access_token)
        return response

    @staticmethod
    def _error(message, status_code):
        return Response(
            {"detail": message},
            status=status_code,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self._authenticate_user(serializer.validated_data)

        if user is None:
            return self._invalid_credentials_response()

        access_token, refresh_token = create_jwt_tokens(user)
        response = self._create_response(user)
        set_auth_cookies(response, access_token, refresh_token)
        return response

    @staticmethod
    def _authenticate_user(data):
        email = data["email"].strip().lower()
        return authenticate(
            username=email,
            password=data["password"],
        )

    @staticmethod
    def _invalid_credentials_response():
        return Response(
            {"detail": "Please check your credentials and try again."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    @staticmethod
    def _create_response(user):
        return Response(
            {
                "detail": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                },
            },
            status=status.HTTP_200_OK,
        )


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)

        if not user or not default_token_generator.check_token(user, token):
            return self._activation_failed_response()

        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "Account successfully activated."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_user(uidb64):
        user_model = get_user_model()

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return user_model.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, user_model.DoesNotExist):
            return None

    @staticmethod
    def _activation_failed_response():
        return Response(
            {"detail": "Activation failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        uid, token = create_activation_credentials(user)

        send_activation_email(user, uid, token)

        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                },
                "token": token,
            },
            status=status.HTTP_201_CREATED,
        )
