#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${CREATE_SUPERUSER:-False}" = "True" ]; then
  python /app/scripts/create_superuser.py
fi

exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --no-control-socket
