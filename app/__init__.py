"""Flask app factory for the B2 video gallery."""

import logging
import os

from flask import Flask, jsonify, render_template

from .b2 import B2ConfigurationError, B2StorageError, list_videos


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        B2_ENDPOINT_URL=os.getenv("B2_ENDPOINT_URL", ""),
        B2_BUCKET_NAME=os.getenv("B2_BUCKET_NAME", ""),
        B2_KEY_ID=os.getenv("B2_KEY_ID", ""),
        B2_APPLICATION_KEY=os.getenv("B2_APPLICATION_KEY", ""),
        B2_REGION=os.getenv("B2_REGION", "us-east-1"),
        B2_PREFIX=os.getenv("B2_PREFIX", ""),
        MAX_VIDEOS=int(os.getenv("MAX_VIDEOS", "200")),
        PRESIGNED_URL_TTL=int(os.getenv("PRESIGNED_URL_TTL", "3600")),
    )
    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def index():
        try:
            videos, truncated = list_videos(app.config)
            return render_template("index.html", videos=videos, truncated=truncated, error=None)
        except B2ConfigurationError:
            app.logger.warning("B2 storage settings are incomplete")
            error = "Storage is not configured yet. Add the required B2 environment variables."
        except B2StorageError:
            app.logger.exception("Unable to load videos from B2")
            error = "Videos could not be loaded right now. Please try again later."
        return render_template("index.html", videos=[], truncated=False, error=error), 503

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    return app


logging.getLogger("boto3").setLevel(logging.WARNING)
