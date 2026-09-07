#!/bin/sh
set -eu

IMAGE="${1:?Usage: scripts/deploy.sh <container-image>}"
COMPOSE_FILE="compose.prod.yaml"
WEB_CONTAINER="videoflix_backend"
WORKER_CONTAINER="videoflix_worker"

previous_image() {
  docker inspect --format '{{.Config.Image}}' "$WEB_CONTAINER" 2>/dev/null || true
}

container_health() {
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$WEB_CONTAINER" 2>/dev/null || true
}

wait_until_healthy() {
  attempts=0
  while [ "$attempts" -lt 18 ]; do
    status="$(container_health)"
    [ "$status" = "healthy" ] && return 0
    [ "$status" = "exited" ] && return 1
    attempts=$((attempts + 1))
    sleep 5
  done
  return 1
}

rollback() {
  old_image="$1"
  case "$old_image" in
    ghcr.io/*)
      echo "Deployment failed. Rolling back to $old_image"
      APP_IMAGE="$old_image" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
      ;;
    *)
      echo "No compatible previous CI/CD image is available for automatic rollback."
      return 1
      ;;
  esac
}

OLD_IMAGE="$(previous_image)"
echo "Deploying $IMAGE"
APP_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" pull web worker
APP_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

if ! wait_until_healthy; then
  APP_IMAGE="$IMAGE" docker compose -f "$COMPOSE_FILE" logs --tail=100 web worker || true
  rollback "$OLD_IMAGE" || true
  exit 1
fi

echo "Deployment healthy."
docker image prune -f >/dev/null 2>&1 || true
