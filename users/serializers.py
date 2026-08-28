from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers


GENERIC_ERROR = "Please check your input and try again."


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirmed_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        attrs["email"] = email
        self._validate_password_match(attrs)
        self._validate_email(email)
        self._validate_password(attrs["password"], email)
        return attrs

    def create(self, validated_data):
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
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(GENERIC_ERROR)

    @staticmethod
    def _validate_email(email):
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(GENERIC_ERROR)

    @staticmethod
    def _validate_password(password, email):
        user = User(username=email, email=email)
        try:
            validate_password(password, user=user)
        except ValidationError:
            raise serializers.ValidationError(GENERIC_ERROR)
