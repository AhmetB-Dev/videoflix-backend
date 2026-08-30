"""Signal handlers that enqueue video processing and invalidate cached video data."""

import django_rq
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import process_video
from .utils import clear_video_list_cache


@receiver(post_save, sender=Video)
def handle_video_save(sender, instance, created, **kwargs):
    """Invalidate cached video data and enqueue processing for new uploads."""
    clear_video_list_cache()

    if created and instance.original_file:
        transaction.on_commit(
            lambda: django_rq.enqueue(
                process_video,
                instance.pk,
            )
        )


@receiver(post_delete, sender=Video)
def handle_video_delete(sender, instance, **kwargs):
    """Invalidate the cached dashboard list after a video is deleted."""
    clear_video_list_cache()
