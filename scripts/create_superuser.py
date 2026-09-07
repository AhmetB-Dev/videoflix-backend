"""Create the configured Django superuser when explicitly enabled."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402


def required_env(name):
    """Return a required environment variable or fail clearly."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_superuser():
    """Create the configured superuser only when it does not already exist."""
    user_model = get_user_model()
    username = required_env("DJANGO_SUPERUSER_USERNAME")
    email = required_env("DJANGO_SUPERUSER_EMAIL")
    password = required_env("DJANGO_SUPERUSER_PASSWORD")
    if user_model.objects.filter(username=username).exists():
        return
    user_model.objects.create_superuser(username, email, password)


if __name__ == "__main__":
    create_superuser()
