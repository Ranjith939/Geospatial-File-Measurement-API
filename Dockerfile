# I keep everything in one image: the Django + DRF API, the pages, and the static files (WhiteNoise serves them).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# I install dependencies first so Docker caches this layer until requirements.txt changes.
# pyogrio and pyproj wheels already bundle GDAL and PROJ, so we don't need any apt packages.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
# If the repo came from a zip download or a Windows clone the exec bit can get lost, and then the container won't start.
RUN chmod +x /app/docker/entrypoint.sh

# collectstatic loads settings, and settings won't load without a SECRET_KEY when DEBUG is off.
# So I pass a throwaway key for this one RUN only. The real key comes from the environment at run time.
RUN SECRET_KEY="build-only-not-a-secret" python manage.py collectstatic --noinput

RUN useradd --create-home appuser && mkdir -p /data/media && chown -R appuser /app /data
USER appuser
ENV MEDIA_ROOT=/data/media

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
