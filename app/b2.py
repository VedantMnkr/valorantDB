"""Backblaze B2 access through its S3-compatible API."""

import logging
import mimetypes
import os

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".ogv", ".ogg", ".mkv"}
REQUIRED_SETTINGS = ("B2_ENDPOINT_URL", "B2_BUCKET_NAME", "B2_KEY_ID", "B2_APPLICATION_KEY")


class B2ConfigurationError(Exception):
    """Raised when required B2 configuration is missing or invalid."""


class B2StorageError(Exception):
    """Raised when the B2 S3-compatible API cannot be used."""


def _client(config):
    missing = [key for key in REQUIRED_SETTINGS if not config.get(key)]
    if missing:
        raise B2ConfigurationError("Missing required B2 settings")

    return boto3.client(
        "s3",
        endpoint_url=config["B2_ENDPOINT_URL"],
        aws_access_key_id=config["B2_KEY_ID"],
        aws_secret_access_key=config["B2_APPLICATION_KEY"],
        region_name=config.get("B2_REGION") or "us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def list_videos(config):
    """Return (video metadata, truncated) without exposing B2 credentials."""
    try:
        client = _client(config)
        bucket = config["B2_BUCKET_NAME"]
        prefix = config.get("B2_PREFIX", "")
        max_videos = max(1, min(int(config.get("MAX_VIDEOS", 200)), 1000))
        url_ttl = max(60, min(int(config.get("PRESIGNED_URL_TTL", 3600)), 604800))
        videos = []
        truncated = False

        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": 100})
        for page in pages:
            for item in page.get("Contents", []):
                key = item.get("Key", "")
                extension = os.path.splitext(key)[1].lower()
                if not key or extension not in VIDEO_EXTENSIONS:
                    continue
                if len(videos) >= max_videos:
                    truncated = True
                    break
                content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
                url = client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                        "ResponseContentType": content_type,
                        "ResponseContentDisposition": "inline",
                    },
                    ExpiresIn=url_ttl,
                )
                videos.append(
                    {
                        "key": key,
                        "name": key.rsplit("/", 1)[-1] or key,
                        "url": url,
                        "content_type": content_type,
                        "size": item.get("Size", 0),
                        "last_modified": item.get("LastModified"),
                    }
                )
            if truncated:
                break
        return videos, truncated
    except (B2ConfigurationError, B2StorageError):
        raise
    except (BotoCoreError, ClientError, ValueError, TypeError) as exc:
        logger.exception("B2 request failed")
        raise B2StorageError("Unable to retrieve videos") from exc
