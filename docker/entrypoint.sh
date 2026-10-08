#!/bin/sh
# Runs on every container start: apply migrations, then hand off to gunicorn.
# Postgres readiness is gated by the compose healthcheck (depends_on: service_healthy).
set -e

python manage.py migrate --noinput

# Uploads are processed inside the request, so the timeout allows for large files.
exec gunicorn geomeasure.wsgi:application \
    --workers "${WEB_WORKERS:-2}" --threads 4 --worker-class gthread \
    --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 \
    --access-logfile - --error-logfile -
