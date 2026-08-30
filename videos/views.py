from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import Video
from .serializers import VideoSerializer


class VideoListView(ListAPIView):
    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Video.objects.filter(processing_status=Video.ProcessingStatus.READY)
