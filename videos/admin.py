from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "processing_status",
        "created_at",
    )
    list_filter = ("category", "processing_status")
    search_fields = ("title", "description")
