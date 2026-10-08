# One image: Django + DRF API, server-rendered pages and static assets (served by WhiteNoise).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so this layer is cached until requirements.txt changes. pyogrio and pyproj
# ship wheels with GDAL/PROJ bundled, so no apt packages are needed.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
# A checkout that drops the mode bit (zip download, some Windows clones) would otherwise fail at start.
RUN chmod +x /app/docker/entrypoint.sh

# collectstatic imports settings, which refuse to start without SECRET_KEY outside DEBUG. A throwaway
# value is scoped to this one RUN; the real key arrives from the environment at run time.
RUN SECRET_KEY="build-only-not-a-secret" python manage.py collectstatic --noinput

RUN useradd --create-home appuser && mkdir -p /data/media && chown -R appuser /app /data
USER appuser
ENV MEDIA_ROOT=/data/media

EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
