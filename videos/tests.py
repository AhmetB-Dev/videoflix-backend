from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Video


import tempfile
from pathlib import Path

from django.test import override_settings


class HLSStreamingTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temp_dir.name)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
        )
        self.settings_override.enable()

        self.user = User.objects.create_user(
            username="stream@test.com",
            email="stream@test.com",
            password="StrongPassword123!",
        )
        self.video = Video.objects.create(
            title="Streaming Test",
            description="Test",
            category="Drama",
            processing_status=Video.ProcessingStatus.READY,
        )
        self.create_hls_files()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_dir.cleanup()

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def create_hls_files(self):
        hls_dir = self.media_root / "videos" / str(self.video.id) / "720p"
        hls_dir.mkdir(parents=True)
        (hls_dir / "index.m3u8").write_text(
            "#EXTM3U\n#EXTINF:10,\n000.ts",
            encoding="utf-8",
        )
        (hls_dir / "000.ts").write_bytes(b"test-segment")

    def test_manifest_requires_authentication(self):
        response = self.client.get(f"/api/video/{self.video.id}/720p/index.m3u8")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_gets_manifest(self):
        self.authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/720p/index.m3u8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.apple.mpegurl",
        )

    def test_authenticated_user_gets_segment(self):
        self.authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/720p/000.ts/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/MP2T")

    def test_invalid_resolution_returns_404(self):
        self.authenticate()

        response = self.client.get(f"/api/video/{self.video.id}/999p/index.m3u8")

        self.assertEqual(response.status_code, 404)

    def test_unknown_video_returns_404(self):
        self.authenticate()

        response = self.client.get("/api/video/999999/720p/index.m3u8")

        self.assertEqual(response.status_code, 404)


class VideoListTests(APITestCase):
    endpoint = "/api/video/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="video@test.com",
            email="video@test.com",
            password="StrongPassword123!",
        )
        cache.clear()

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def create_video(
        self,
        title,
        status=Video.ProcessingStatus.READY,
    ):
        return Video.objects.create(
            title=title,
            description="Test description",
            category="Drama",
            processing_status=status,
        )

    def test_unauthenticated_user_gets_401(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 401)

    def test_only_ready_videos_are_returned(self):
        self.authenticate()
        ready_video = self.create_video("Ready")
        self.create_video(
            "Pending",
            Video.ProcessingStatus.PENDING,
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], ready_video.id)
        self.assertEqual(len(response.data), 1)

    def test_videos_are_ordered_newest_first(self):
        self.authenticate()
        older = self.create_video("Older")
        newer = self.create_video("Newer")
        now = timezone.now()

        Video.objects.filter(pk=older.pk).update(
            created_at=now - timedelta(days=1),
        )
        Video.objects.filter(pk=newer.pk).update(created_at=now)
        cache.clear()

        response = self.client.get(self.endpoint)

        self.assertEqual(
            [item["id"] for item in response.data],
            [newer.id, older.id],
        )

    def test_video_list_is_cached(self):
        self.authenticate()
        self.create_video("Cached video")

        self.client.get(self.endpoint)

        self.assertIsNotNone(cache.get("video_list"))

    def test_video_save_invalidates_cache(self):
        self.authenticate()
        video = self.create_video("Old title")
        self.client.get(self.endpoint)

        self.assertIsNotNone(cache.get("video_list"))

        video.title = "New title"
        video.save(update_fields=["title"])

        self.assertIsNone(cache.get("video_list"))
