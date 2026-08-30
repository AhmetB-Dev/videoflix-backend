import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Video
from .tasks import process_video


class VideoListTests(APITestCase):
    endpoint = "/api/video/"

    def setUp(self):
        self.user = self.create_user()
        cache.clear()

    @staticmethod
    def create_user():
        return User.objects.create_user(
            username="video@test.com",
            email="video@test.com",
            password="StrongPassword123!",
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    @staticmethod
    def create_video(title, status=Video.ProcessingStatus.READY):
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
        self.create_video("Pending", Video.ProcessingStatus.PENDING)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], ready_video.id)
        self.assertEqual(len(response.data), 1)

    def test_videos_are_ordered_newest_first(self):
        self.authenticate()
        older = self.create_video("Older")
        newer = self.create_video("Newer")
        self.set_video_dates(older, newer)
        response = self.client.get(self.endpoint)
        video_ids = [item["id"] for item in response.data]
        self.assertEqual(video_ids, [newer.id, older.id])

    @staticmethod
    def set_video_dates(older, newer):
        now = timezone.now()
        Video.objects.filter(pk=older.pk).update(
            created_at=now - timedelta(days=1),
        )
        Video.objects.filter(pk=newer.pk).update(created_at=now)
        cache.clear()

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


class HLSStreamingTests(APITestCase):
    def setUp(self):
        self.create_temp_media()
        self.user = self.create_user()
        self.video = self.create_video()
        self.create_hls_files()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_dir.cleanup()

    def create_temp_media(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temp_dir.name)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
        )
        self.settings_override.enable()

    @staticmethod
    def create_user():
        return User.objects.create_user(
            username="stream@test.com",
            email="stream@test.com",
            password="StrongPassword123!",
        )

    @staticmethod
    def create_video():
        return Video.objects.create(
            title="Streaming Test",
            description="Test",
            category="Drama",
            processing_status=Video.ProcessingStatus.READY,
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def get_hls_directory(self):
        return self.media_root / "videos" / str(self.video.id) / "720p"

    def create_hls_files(self):
        hls_dir = self.get_hls_directory()
        hls_dir.mkdir(parents=True)
        manifest = "#EXTM3U\n#EXTINF:10,\n000.ts"
        (hls_dir / "index.m3u8").write_text(
            manifest,
            encoding="utf-8",
        )
        (hls_dir / "000.ts").write_bytes(b"test-segment")

    def manifest_url(self, video_id=None, resolution="720p"):
        movie_id = video_id or self.video.id
        return f"/api/video/{movie_id}/{resolution}/index.m3u8"

    def segment_url(self):
        return f"/api/video/{self.video.id}/720p/000.ts/"

    def test_manifest_requires_authentication(self):
        response = self.client.get(self.manifest_url())
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_gets_manifest(self):
        self.authenticate()
        response = self.client.get(self.manifest_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.apple.mpegurl",
        )

    def test_authenticated_user_gets_segment(self):
        self.authenticate()
        response = self.client.get(self.segment_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/MP2T")

    def test_invalid_resolution_returns_404(self):
        self.authenticate()
        response = self.client.get(self.manifest_url(resolution="999p"))
        self.assertEqual(response.status_code, 404)

    def test_unknown_video_returns_404(self):
        self.authenticate()
        response = self.client.get(self.manifest_url(video_id=999999))
        self.assertEqual(response.status_code, 404)


class VideoTaskTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.temp_dir.name)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
        )
        self.settings_override.enable()
        self.video = self.create_video()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_dir.cleanup()

    @staticmethod
    def create_video():
        return Video.objects.create(
            title="Task Test",
            description="Test",
            category="Drama",
            original_file="videos/originals/test.mp4",
        )

    @patch("videos.tasks.subprocess.run")
    def test_process_video_sets_ready_status(self, mock_run):
        process_video(self.video.pk)
        self.video.refresh_from_db()

        self.assertEqual(
            self.video.processing_status,
            Video.ProcessingStatus.READY,
        )
        self.assertTrue(self.video.thumbnail.name.endswith(".jpg"))
        self.assertEqual(mock_run.call_count, 4)

    @patch("videos.tasks.subprocess.run")
    def test_process_video_sets_failed_status(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            "ffmpeg",
        )

        with self.assertRaises(subprocess.CalledProcessError):
            process_video(self.video.pk)

        self.video.refresh_from_db()
        self.assertEqual(
            self.video.processing_status,
            Video.ProcessingStatus.FAILED,
        )
