"""Settings for the test runners (pytest unit/API suites and the Playwright E2E suite).

Plain static storage, no manifest: production hashes static filenames after collectstatic,
and a fresh clone must be able to run its own tests without a build step.
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

# WhiteNoise warns when STATIC_ROOT is missing (before any collectstatic); serve via finders instead.
WHITENOISE_USE_FINDERS = True
STATIC_ROOT.mkdir(exist_ok=True)  # noqa: F405

# A file-backed test database: an in-memory SQLite DB cannot be shared with the live_server
# threads the browser suite runs in, which breaks a single `pytest` run of all suites.
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):  # noqa: F405
    DATABASES["default"]["TEST"] = {"NAME": str(MEDIA_ROOT.parent / "geomeasure-test.db")}  # noqa: F405
