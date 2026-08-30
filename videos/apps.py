"""Django application configuration for the videos app."""

from django.apps import AppConfig


class VideosConfig(AppConfig):
    """Configure the videos app and register its signal handlers on startup."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "videos"

    def ready(self):
        """Import signal handlers once Django has loaded the videos application."""
        import videos.signals  # noqa: F401
