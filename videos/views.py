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
        content = get_manifest_content(movie_id, resolution)

        if content is None:
            return HttpResponse(status=404)

        return HttpResponse(
            content,
            content_type="application/vnd.apple.mpegurl",
        )


class HLSSegmentView(APIView):
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
