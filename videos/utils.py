"""Helpers for video caching and safe access to HLS manifests and segments."""

from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from .models import Video

ALLOWED_RESOLUTIONS = {"480p", "720p", "1080p"}

VIDEO_LIST_CACHE_KEY = "video_list"
VIDEO_LIST_CACHE_TIMEOUT = 300


def get_manifest_content(movie_id, resolution):
    """Return the requested HLS manifest content when the generated file exists."""
    get_ready_video(movie_id)
    manifest_path = get_manifest_path(movie_id, resolution)

    if not manifest_path or not manifest_path.exists():
        return None

    return manifest_path.read_text(encoding="utf-8")


def get_existing_segment_path(movie_id, resolution, segment):
    """Return a validated HLS segment path when the generated file exists."""
    get_ready_video(movie_id)
    segment_path = get_segment_path(movie_id, resolution, segment)

    if not segment_path or not segment_path.exists():
        return None

    return segment_path


def get_thumbnail_path(movie_id):
    """Return a ready video's generated thumbnail path when it exists."""
    video = get_ready_video(movie_id)
    if not video.thumbnail:
        return None
    thumbnail_path = Path(video.thumbnail.path)
    return thumbnail_path if thumbnail_path.exists() else None


def get_cached_video_list():
    """Read the serialized dashboard video list from Redis-backed cache."""
    return cache.get(VIDEO_LIST_CACHE_KEY)


def cache_video_list(data):
    """Cache the serialized dashboard video list for a short period."""
    cache.set(
        VIDEO_LIST_CACHE_KEY,
        data,
        VIDEO_LIST_CACHE_TIMEOUT,
    )


def clear_video_list_cache():
    """Invalidate the cached dashboard video list."""
    cache.delete(VIDEO_LIST_CACHE_KEY)


def get_ready_video(movie_id):
    """Return a ready video or raise a 404 response when it is unavailable."""
    return get_object_or_404(
        Video,
        pk=movie_id,
        processing_status=Video.ProcessingStatus.READY,
    )


def get_hls_directory(movie_id, resolution):
    """Return the generated HLS directory for an allowed resolution."""
    if resolution not in ALLOWED_RESOLUTIONS:
        return None

    return Path(settings.MEDIA_ROOT) / "videos" / str(movie_id) / resolution


def get_manifest_path(movie_id, resolution):
    """Return the expected index.m3u8 path for a video and resolution."""
    directory = get_hls_directory(movie_id, resolution)

    if directory is None:
        return None

    return directory / "index.m3u8"


def get_segment_path(movie_id, resolution, segment):
    """Return a safe HLS segment path after validating the segment name."""
    if not is_valid_segment(segment):
        return None

    directory = get_hls_directory(movie_id, resolution)

    if directory is None:
        return None

    return directory / segment


def is_valid_segment(segment):
    """Allow only plain .ts filenames without directory traversal components."""
    return Path(segment).name == segment and segment.endswith(".ts")
