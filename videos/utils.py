from pathlib import Path
from django.core.cache import cache

from django.conf import settings


ALLOWED_RESOLUTIONS = {"480p", "720p", "1080p"}

VIDEO_LIST_CACHE_KEY = "video_list"
VIDEO_LIST_CACHE_TIMEOUT = 300


def get_cached_video_list():
    return cache.get(VIDEO_LIST_CACHE_KEY)


def cache_video_list(data):
    cache.set(
        VIDEO_LIST_CACHE_KEY,
        data,
        VIDEO_LIST_CACHE_TIMEOUT,
    )


def clear_video_list_cache():
    cache.delete(VIDEO_LIST_CACHE_KEY)


def get_hls_directory(movie_id, resolution):
    if resolution not in ALLOWED_RESOLUTIONS:
        return None

    return Path(settings.MEDIA_ROOT) / "videos" / str(movie_id) / resolution


def get_manifest_path(movie_id, resolution):
    directory = get_hls_directory(movie_id, resolution)

    if directory is None:
        return None

    return directory / "index.m3u8"


def get_segment_path(movie_id, resolution, segment):
    if not is_valid_segment(segment):
        return None

    directory = get_hls_directory(movie_id, resolution)

    if directory is None:
        return None

    return directory / segment


def is_valid_segment(segment):
    return Path(segment).name == segment and segment.endswith(".ts")
