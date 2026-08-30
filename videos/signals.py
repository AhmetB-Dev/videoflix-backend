import django_rq

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Video
from .tasks import process_video


@receiver(post_save, sender=Video)
def enqueue_video_processing(sender, instance, created, **kwargs):
    if not created or not instance.original_file:
        return

    transaction.on_commit(lambda: django_rq.enqueue(process_video, instance.pk))
