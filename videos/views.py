from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Video
from .serializers import VideoSerializer
from .utils import get_manifest_path, get_segment_path


class VideoListView(ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Video.objects.filter(processing_status=Video.ProcessingStatus.READY)


class HLSManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        self._ensure_video_exists(movie_id)
        manifest_path = get_manifest_path(movie_id, resolution)

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
            open(segment_path, "rb"),
            content_type="video/MP2T",
        )

    @staticmethod
    def _ensure_video_exists(movie_id):
        return get_object_or_404(
            Video,
            pk=movie_id,
            processing_status=Video.ProcessingStatus.READY,
        )


class VideoListView(ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Video.objects.filter(processing_status=Video.ProcessingStatus.READY)
