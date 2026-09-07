#!/bin/sh
set -eu

wait_for_postgres() {
  echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
  until pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -q; do
    sleep 1
  done
  echo "PostgreSQL is ready."
}

prepare_writable_directories() {
  if [ "$(id -u)" != "0" ]; then
    return
  fi

  mkdir -p /app/media
  chown -R app:app /app/media

  if [ "${PREPARE_STATIC_DIR:-False}" = "True" ]; then
    mkdir -p /app/static
    chown -R app:app /app/static
  fi
}

run_as_app_user() {
  if [ "$(id -u)" = "0" ]; then
    exec gosu app "$@"
  fi
  exec "$@"
}

wait_for_postgres
prepare_writable_directories
run_as_app_user "$@"
