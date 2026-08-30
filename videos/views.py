from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Video
from .serializers import VideoSerializer
from .utils import (
    cache_video_list,
    get_cached_video_list,
    get_manifest_path,
    get_segment_path,
)


class VideoListView(ListAPIView):
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


class HLSManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        self._ensure_video_exists(movie_id)
        manifest_path = get_manifest_path(
            movie_id,
            resolution,
        )

        if not manifest_path or not manifest_path.exists():
            return HttpResponse(status=404)

        content = manifest_path.read_text(encoding="utf-8")
        return HttpResponse(
            content,
            content_type="application/vnd.apple.mpegurl",
        )

    @staticmethod
    def _ensure_video_exists(movie_id):
        return get_object_or_404(
            Video,
            pk=movie_id,
            processing_status=Video.ProcessingStatus.READY,
        )


class HLSSegmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        self._ensure_video_exists(movie_id)
        segment_path = get_segment_path(
            movie_id,
            resolution,
            segment,
        )

        if not segment_path or not segment_path.exists():
            return HttpResponse(status=404)

        return FileResponse(
            segment_path.open("rb"),
            content_type="video/MP2T",
        )

    @staticmethod
    def _ensure_video_exists(movie_id):
        return get_object_or_404(
            Video,
            pk=movie_id,
            processing_status=Video.ProcessingStatus.READY,
        )
