"""Django settings for GeoMeasure.

I read secrets and deployment switches from environment variables (or a local .env file)
with python-decouple. Every variable we use is listed in .env.example.
"""

from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY is not set. Put it in .env (see .env.example).")
    SECRET_KEY = "dev-only-insecure-key"  # only for DEBUG=True, production never sees this
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "core",
    "processing",
    "api",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "geomeasure.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "geomeasure.wsgi.application"


def _database_from_url(url):
    """Turns DATABASE_URL into Django config. I support sqlite:///geomeasure.db (default) or postgres://user:pass@host:port/name."""
    parsed = urlparse(url)
    if parsed.scheme in ("postgres", "postgresql"):
        entry = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
        if options := dict(parse_qsl(parsed.query)):
            entry["OPTIONS"] = options
        return entry
    if parsed.scheme == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / (unquote(parsed.path.lstrip("/")) or "geomeasure.db")}
    raise ImproperlyConfigured(f"Unsupported DATABASE_URL scheme: {parsed.scheme!r}")


DATABASES = {"default": _database_from_url(config("DATABASE_URL", default="sqlite:///geomeasure.db"))}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Uploads ------------------------------------------------------------------
MAX_UPLOAD_MB = config("MAX_UPLOAD_MB", default=50, cast=int)
# These two stop zip bombs. An archive can't unpack to more than this many MB or this many files.
MAX_EXTRACTED_MB = config("MAX_EXTRACTED_MB", default=500, cast=int)
MAX_ARCHIVE_MEMBERS = config("MAX_ARCHIVE_MEMBERS", default=1000, cast=int)
# Anything bigger than this goes to a temp file instead of memory. The real upload limit is MAX_UPLOAD_MB.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# --- API ------------------------------------------------------------------------
# The UI is served by this same app, so I didn't set up CORS and other origins get refused.
# If we ever host the frontend somewhere else, add django-cors-headers.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.MultiPartParser", "rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "api.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "GeoMeasure API",
    "DESCRIPTION": "Upload KML or zipped Shapefiles; get features, CRS and projected measurements back.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Security -------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL = config("SECURE_SSL", default=False, cast=bool)
if SECURE_SSL:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000

# --- Logging: the "geomeasure" logger writes one JSON object per line ----------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(levelname)-5s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "loggers": {
        "geomeasure": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO"), "propagate": False},
        "django": {"handlers": ["console"], "level": "WARNING"},
    },
}
