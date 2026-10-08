"""Settings I use for all the tests (pytest unit/API tests and the Playwright E2E tests).

I switched to plain static storage here, no manifest. Production hashes static filenames after
collectstatic, but I want a fresh clone to run its tests without any build step.
"""
import tempfile
from pathlib import Path

from .settings import *  # noqa: F401,F403

SECRET_KEY = "test-not-secret"
DEBUG = False
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="geomeasure-test-media-"))
MAX_UPLOAD_MB = 2
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# WhiteNoise complains if STATIC_ROOT doesn't exist yet (no collectstatic), so I create it and let the finders serve files.
WHITENOISE_USE_FINDERS = True
STATIC_ROOT.mkdir(exist_ok=True)  # noqa: F405

# I use a file for the test database. An in-memory SQLite DB can't be shared with the live_server
# threads the browser tests run in, and that broke running everything with a single `pytest`.
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):  # noqa: F405
    DATABASES["default"]["TEST"] = {"NAME": str(MEDIA_ROOT.parent / "geomeasure-test.db")}  # noqa: F405
