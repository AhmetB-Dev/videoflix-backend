"""DRF serializers for exposing processed video metadata through the API."""

from rest_framework import serializers

from .models import Video


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
        """Return an absolute thumbnail URL or None when no thumbnail exists."""
        if not video.thumbnail:
            return None

        request = self.context.get("request")
        return request.build_absolute_uri(video.thumbnail.url)
