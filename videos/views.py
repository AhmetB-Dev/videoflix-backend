"""Authenticated API views for the video dashboard and HLS delivery."""

from django.http import FileResponse, HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Video
from .serializers import VideoSerializer
from .utils import (
    cache_video_list,
    get_cached_video_list,
    get_existing_segment_path,
    get_manifest_content,
    get_thumbnail_path,
)


class VideoListView(ListAPIView):
    """Return ready videos and cache the serialized dashboard response.

    Only authenticated users can access the list. Cached data is invalidated by
    model signals whenever videos are saved or deleted."""
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    queryset = Video.objects.filter(processing_status=Video.ProcessingStatus.READY)

    def list(self, request, *args, **kwargs):
        cached_data = get_cached_video_list()
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache_video_list(response.data)
        return response


class VideoThumbnailView(APIView):
    """Serve a generated thumbnail only to authenticated users."""
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id):
        thumbnail_path = get_thumbnail_path(movie_id)
        if thumbnail_path is None:
            return HttpResponse(status=404)
        return FileResponse(
            thumbnail_path.open("rb"),
            content_type="image/jpeg",
        )


class HLSManifestView(APIView):
    """Serve an authenticated HLS playlist for a ready video and resolution."""
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        content = get_manifest_content(movie_id, resolution)

        if content is None:
            return HttpResponse(status=404)

        return HttpResponse(
            content,
            content_type="application/vnd.apple.mpegurl",
        )


class HLSSegmentView(APIView):
    """Serve authenticated HLS transport-stream segments from validated paths.

    Segment names and resolutions are checked before filesystem access to avoid
    serving arbitrary files outside the generated HLS directories."""
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        segment_path = get_existing_segment_path(
            movie_id,
            resolution,
            segment,
        )

        if segment_path is None:
            return HttpResponse(status=404)

        return FileResponse(
            segment_path.open("rb"),
            content_type="video/MP2T",
        )
