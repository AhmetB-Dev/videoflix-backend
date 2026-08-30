import subprocess
from pathlib import Path

from django.conf import settings

from .models import Video


RESOLUTIONS = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}


def process_video(video_id):
    video = Video.objects.get(pk=video_id)
    _set_status(video, Video.ProcessingStatus.PROCESSING)

    try:
        _create_thumbnail(video)
        _create_hls_versions(video)
        _set_status(video, Video.ProcessingStatus.READY)
    except Exception:
        _set_status(video, Video.ProcessingStatus.FAILED)
        raise


def _create_hls_versions(video):
    for resolution, height in RESOLUTIONS.items():
        _create_hls_version(video, resolution, height)


def _create_hls_version(video, resolution, height):
    output_dir = _output_dir(video, resolution)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = _hls_command(video, output_dir, height)
    subprocess.run(command, check=True)


def _hls_command(video, output_dir, height):
    return [
        "ffmpeg",
        "-y",
        "-i",
        video.original_file.path,
        "-vf",
        f"scale=-2:{height}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-hls_time",
        "10",
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        str(output_dir / "%03d.ts"),
        str(output_dir / "index.m3u8"),
    ]


def _create_thumbnail(video):
    thumbnail_path = _thumbnail_path(video)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(_thumbnail_command(video, thumbnail_path), check=True)
    video.thumbnail.name = _relative_media_path(thumbnail_path)
    video.save(update_fields=["thumbnail"])


def _thumbnail_command(video, output_path):
    return [
        "ffmpeg",
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        video.original_file.path,
        "-frames:v",
        "1",
        str(output_path),
    ]


def _output_dir(video, resolution):
    return Path(settings.MEDIA_ROOT) / "videos" / str(video.pk) / resolution


def _thumbnail_path(video):
    return Path(settings.MEDIA_ROOT) / "videos" / "thumbnails" / f"{video.pk}.jpg"


def _relative_media_path(path):
    return str(path.relative_to(settings.MEDIA_ROOT))


def _set_status(video, new_status):
    video.processing_status = new_status
    video.save(update_fields=["processing_status"])
