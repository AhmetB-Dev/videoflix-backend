#!/bin/sh
set -eu

IMAGE="${1:?Usage: scripts/deploy.sh <container-image>}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yaml}"
APP_SERVICE="${APP_SERVICE:-web}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"

current_image() {
  container_id="$(docker compose -f "$COMPOSE_FILE" ps -q "$APP_SERVICE" 2>/dev/null || true)"
  [ -n "$container_id" ] || return 0
  docker inspect --format '{{.Config.Image}}' "$container_id" 2>/dev/null || true
}

rollback() {
  old_image="$1"
  [ -n "$old_image" ] || return 1
  echo "Rolling application image back to $old_image"
  APP_IMAGE="$old_image" docker compose -f "$COMPOSE_FILE" up \
    -d --remove-orphans --wait --wait-timeout "$WAIT_TIMEOUT"
}

OLD_IMAGE="$(current_image)"
echo "Deploying $IMAGE"

APP_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" pull

if APP_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" up \
  -d --remove-orphans --wait --wait-timeout "$WAIT_TIMEOUT"; then
  echo "Deployment healthy."
  docker image prune -f >/dev/null 2>&1 || true
  exit 0
fi

echo "Deployment failed."
docker compose -f "$COMPOSE_FILE" logs --tail=150 || true
rollback "$OLD_IMAGE" || echo "Automatic application-image rollback was not possible."
exit 1
