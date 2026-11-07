from datetime import datetime, timezone
from unittest.mock import patch

from app import create_app
from app.b2 import B2StorageError


class FakePaginator:
    def paginate(self, **kwargs):
        assert kwargs["Bucket"] == "test-bucket"
        return [{
            "Contents": [
                {"Key": "videos/clip.mp4", "Size": 2_097_152, "LastModified": datetime(2025, 1, 2, tzinfo=timezone.utc)},
                {"Key": "notes.txt", "Size": 100},
            ]
        }]


class FakeS3:
    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return FakePaginator()

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        assert operation == "get_object"
        assert Params["Bucket"] == "test-bucket"
        assert ExpiresIn == 3600
        return "https://example.invalid/signed-video"


def configured_app():
    return create_app({
        "TESTING": True,
        "B2_ENDPOINT_URL": "https://s3.example.invalid",
        "B2_BUCKET_NAME": "test-bucket",
        "B2_KEY_ID": "test-key",
        "B2_APPLICATION_KEY": "test-secret",
        "B2_REGION": "us-east-1",
        "B2_PREFIX": "videos/",
        "MAX_VIDEOS": 200,
        "PRESIGNED_URL_TTL": 3600,
    })


def test_index_renders_signed_video_and_skips_non_video():
    app = configured_app()
    with patch("app.b2._client", return_value=FakeS3()):
        response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"clip.mp4" in response.data
    assert b"example.invalid/signed-video" in response.data
    assert b"notes.txt" not in response.data


def test_index_shows_configuration_message_when_b2_is_missing():
    app = create_app({"TESTING": True, "B2_ENDPOINT_URL": ""})
    response = app.test_client().get("/")

    assert response.status_code == 503
    assert b"Storage is not configured" in response.data
    assert b"test-secret" not in response.data


def test_index_handles_storage_failure_without_leaking_details():
    app = configured_app()
    with patch("app.b2._client", side_effect=B2StorageError("sensitive detail")):
        response = app.test_client().get("/")

    assert response.status_code == 503
    assert b"could not be loaded" in response.data
    assert b"sensitive detail" not in response.data


def test_health_endpoint():
    response = create_app({"TESTING": True}).test_client().get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
