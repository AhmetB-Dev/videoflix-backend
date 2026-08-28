from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegistrationSerializer
from .utils import (
    create_activation_credentials,
    create_jwt_tokens,
    send_activation_email,
    set_auth_cookies,
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self._authenticate_user(serializer.validated_data)

        if user is None:
            return Response(
                {"detail": "Please check your credentials and try again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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
            return Response(
                {"detail": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {"message": "Account successfully activated."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_user(uidb64):
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return get_user_model().objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
            return None


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
