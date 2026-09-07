"""Signal handlers for video processing, media cleanup, and cache invalidation."""

import django_rq
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Video
from .tasks import process_video
from .utils import (
    clear_video_list_cache,
    delete_generated_video_media,
    delete_video_media,
)


@receiver(pre_save, sender=Video)
def track_original_file_change(sender, instance, update_fields=None, **kwargs):
    """Remember whether an existing video's source file is being replaced."""
    instance._original_file_changed = False
    instance._previous_original_file_name = None

    if instance._state.adding:
        return
    if update_fields is not None and "original_file" not in update_fields:
        return

    previous = Video.objects.filter(pk=instance.pk).only("original_file").first()
    if previous is None:
        return

    previous_name = previous.original_file.name
    instance._previous_original_file_name = previous_name
    instance._original_file_changed = previous_name != instance.original_file.name


@receiver(post_save, sender=Video)
def handle_video_save(sender, instance, created, **kwargs):
    """Invalidate cached data and enqueue processing for new or replaced sources."""
    clear_video_list_cache()

    source_changed = created or getattr(instance, "_original_file_changed", False)
    if not source_changed or not instance.original_file:
        return

    if not created:
        previous_name = getattr(instance, "_previous_original_file_name", None)
        source_storage = instance.original_file.storage
        thumbnail_storage = instance.thumbnail.storage if instance.thumbnail else None
        thumbnail_name = instance.thumbnail.name if instance.thumbnail else None
        video_id = instance.pk
        Video.objects.filter(pk=video_id).update(
            processing_status=Video.ProcessingStatus.PENDING,
            thumbnail=None,
        )
        transaction.on_commit(
            lambda: delete_generated_video_media(
                video_id,
                thumbnail_storage,
                thumbnail_name,
            ),
            robust=True,
        )
        if previous_name:
            transaction.on_commit(
                lambda: source_storage.delete(previous_name),
                robust=True,
            )

    video_id = instance.pk
    transaction.on_commit(
        lambda: django_rq.enqueue(process_video, video_id),
        robust=True,
    )


@receiver(post_delete, sender=Video)
def handle_video_delete(sender, instance, **kwargs):
    """Invalidate cached data and remove media after a committed video deletion."""
    clear_video_list_cache()
    video_id = instance.pk
    original_storage = instance.original_file.storage
    original_name = instance.original_file.name
    thumbnail_storage = instance.thumbnail.storage if instance.thumbnail else None
    thumbnail_name = instance.thumbnail.name if instance.thumbnail else None
    transaction.on_commit(
        lambda: delete_video_media(
            video_id,
            original_storage,
            original_name,
            thumbnail_storage,
            thumbnail_name,
        ),
        robust=True,
    )
