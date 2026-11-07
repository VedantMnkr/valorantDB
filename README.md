# Frame / Library

A small Flask web service that lists video files from a Backblaze B2 bucket and plays them in a responsive HTML gallery. It uses B2's S3-compatible API and creates time-limited, signed links for private video objects; no credentials are sent to the browser.

## Requirements

- Python 3.11+
- A Backblaze B2 bucket and application key with read/list access to that bucket

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the B2 values. The app does not load `.env` automatically; export those values in your shell or use a local environment-file runner such as `python-dotenv` if you add it.
4. Start the development server with `flask --app 'app:create_app()' run --debug`.
5. Open `http://127.0.0.1:5000`.

Run tests with `pytest`.

## Backblaze B2 setup

1. In Backblaze, create or choose a bucket and note its bucket name and region/endpoint. The S3 endpoint format is `https://s3.<region>.backblazeb2.com` (for example, `https://s3.us-west-004.backblazeb2.com`).
2. Create an application key restricted to the bucket with `listFiles` and `readFiles` permissions. Use the key ID for `B2_KEY_ID` and the application key for `B2_APPLICATION_KEY`.
3. Set `B2_ENDPOINT_URL`, `B2_BUCKET_NAME`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, and `B2_REGION`. The default region setting is `us-east-1`; set it to the region associated with the selected endpoint if required by your bucket.
4. Optionally set `B2_PREFIX` to restrict the gallery to a key prefix such as `videos/`.

Supported extensions are `.mp4`, `.m4v`, `.mov`, `.webm`, `.ogv`, `.ogg`, and `.mkv`. `MAX_VIDEOS` limits the number of items shown (maximum 1000); `PRESIGNED_URL_TTL` sets signed-link lifetime in seconds (60 seconds to 7 days). Signed links allow private bucket playback and expire after the configured duration.

## Deploy to Render

1. Push this repository to a Git provider supported by Render.
2. In Render, create a **Blueprint** and select the repository. Render reads `render.yaml` and creates a Python Web Service.
3. In the service's **Environment** settings, add the B2 values listed above. The `sync: false` entries in the Blueprint deliberately require secrets to be entered in Render's dashboard; never commit them.
4. Deploy. Render runs `pip install -r requirements.txt`, starts Gunicorn, and checks `/health`.

You can alternatively create a Web Service manually with build command `pip install -r requirements.txt` and start command `gunicorn 'app:create_app()'`, then add the same environment variables. Keep the bucket private and use a narrowly scoped application key.

## Troubleshooting

- **Storage is not configured:** check that all four required `B2_*` values are set in the Render environment and redeploy/restart.
- **The library cannot load videos:** confirm the endpoint matches the bucket's region and the application key has `listFiles` and `readFiles` permissions for that bucket.
- **A video link expires:** links are intentionally temporary; reload the page to request a fresh URL or increase `PRESIGNED_URL_TTL` within the allowed range.
- **A video does not play:** verify the file uses a supported extension and browser-compatible encoding (MP4/H.264 is a widely supported choice).
- **Health check passes but the page is unavailable:** `/health` confirms the web process is running; it does not make an external B2 request.
