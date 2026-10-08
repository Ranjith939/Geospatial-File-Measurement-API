#!/bin/sh
# This runs every time the container starts. I apply migrations first and then hand over to gunicorn.
# We don't wait for Postgres here, the compose healthcheck (depends_on: service_healthy) handles that.
set -e

python manage.py migrate --noinput

# Uploads get processed inside the request, so I keep the timeout long enough for big files.
exec gunicorn geomeasure.wsgi:application \
    --workers "${WEB_WORKERS:-2}" --threads 4 --worker-class gthread \
    --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 \
    --access-logfile - --error-logfile -
