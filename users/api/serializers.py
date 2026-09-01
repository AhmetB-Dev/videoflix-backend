"""DRF serializers for authentication, registration, and password recovery."""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

GENERIC_ERROR = "Please check your input and try again."


class PasswordResetSerializer(serializers.Serializer):
    """Validate the email address submitted for a password-reset request."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Validate matching replacement passwords using Django password validators."""

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate serializer input and return normalized attributes."""
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(GENERIC_ERROR)

        self._validate_password(attrs["new_password"])
        return attrs

    @staticmethod
    def _validate_password(password):
        """Apply Django password-strength validation using a generic API error."""
        try:
            validate_password(password)
        except ValidationError:
            raise serializers.ValidationError(GENERIC_ERROR)


class LoginSerializer(serializers.Serializer):
    """Validate the credentials submitted to the login endpoint."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RegistrationSerializer(serializers.Serializer):
    """Validate registration data and create an inactive Django user.

    Accounts remain inactive until the activation token from the confirmation
    email has been successfully verified."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirmed_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate serializer input and return normalized attributes."""
        email = attrs["email"].strip().lower()
        attrs["email"] = email
        self._validate_password_match(attrs)
        self._validate_email(email)
        self._validate_password(attrs["password"], email)
        return attrs

    def create(self, validated_data):
        """Create an inactive user after registration data has been validated."""
        validated_data.pop("confirmed_password")
        email = validated_data["email"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            is_active=False,
        )

    @staticmethod
    def _validate_password_match(attrs):
        """Reject registration when password confirmation does not match."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(GENERIC_ERROR)

    @staticmethod
    def _validate_email(email):
        """Reject email addresses that are already registered."""
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(GENERIC_ERROR)

    @staticmethod
    def _validate_password(password, email):
        """Apply Django password-strength validation using a generic API error."""
        user = User(username=email, email=email)
        try:
            validate_password(password, user=user)
        except ValidationError:
            raise serializers.ValidationError(GENERIC_ERROR)
