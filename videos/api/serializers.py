"""DRF serializers for exposing processed video metadata through the API."""

from django.urls import reverse
from rest_framework import serializers

from ..models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Serialize ready video metadata for the authenticated dashboard."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            "id",
            "created_at",
            "title",
            "description",
            "thumbnail_url",
            "category",
        )

    def get_thumbnail_url(self, video):
        """Return the authenticated API URL for a generated thumbnail."""
        if not video.thumbnail:
            return None

        thumbnail_url = reverse(
            "video-thumbnail",
            kwargs={"movie_id": video.pk},
        )
        request = self.context.get("request")
        return request.build_absolute_uri(thumbnail_url)
