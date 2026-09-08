# Production Deployment

This repository uses the reusable workflows from `AhmetB-Dev/django-devops-template` and a Docker-first CI/CD flow:

1. Pull requests and pushes run Ruff, `pip-audit`, Django checks including a production-style `check --deploy`, the complete test suite, and a 95% coverage gate.
2. A successful push to `main` builds one immutable application image.
3. The image is published to GitHub Container Registry (GHCR).
4. GitHub Actions connects to the VPS via SSH and deploys that exact image tag.
5. The deployment script waits for the web container health check and rolls the application image back if the new container does not become healthy.

Database migrations are still applied by the web startup command. Image rollback therefore does not automatically reverse database migrations; schema changes should remain backward compatible during deployments.

## Database and Redis image versions

Production deliberately does not choose a PostgreSQL or Redis major version automatically. Before the first deployment, check the versions currently running on the VPS and set `POSTGRES_IMAGE` and `REDIS_IMAGE` in the production `.env`.

```bash
docker compose -f compose.prod.yaml exec db postgres --version
docker compose -f compose.prod.yaml exec redis redis-server --version
```

Do not perform a PostgreSQL major upgrade by only changing the Docker image tag. Plan and test the database upgrade separately. The local and CI stacks use explicit fresh-environment defaults and do not reuse production database volumes.

## Production architecture

```text
Internet
   |
   v
Host Nginx / TLS
   |
   v
127.0.0.1:${APP_PORT} (8000 by default for the existing Videoflix VPS)
   |
   +--> web (Gunicorn / Django)
   |
   +--> worker (Django RQ) --> Redis
   |
   +--> PostgreSQL
```

PostgreSQL and Redis are not published to the host. Gunicorn is published only on the loopback interface, so the public entry point remains Nginx.

## One-time VPS preparation

The VPS must already have Docker Engine, Docker Compose, Git, Nginx and TLS configured. Videoflix keeps its own Compose project name, volumes, network and port so it can coexist with other Django deployments on the same server.

Keep the repository at a stable path, for example:

```bash
/home/ahmet/apps/videoflix-backend
```

Create the real production environment file from the template and keep it outside Git:

```bash
cp .env.production.example .env
nano .env
```

Before switching an existing database container to the pinned PostgreSQL image, verify the currently running major version:

```bash
docker compose -f compose.prod.yaml exec db postgres --version
```

Set `POSTGRES_IMAGE` to the exact image family compatible with the existing production data directory. If a major-version upgrade is desired later, perform it as a separate, tested database migration.

## GitHub Actions configuration

The small project workflow in `.github/workflows/cicd.yml` calls the central reusable CI, publish, and deploy workflows. While the deployment template is still being tested, the project references `@main`; after the first stable release it should be pinned to a version tag or commit SHA.

Repository variables:

- `VPS_USER` - SSH user, for example `ahmet`
- `VPS_APP_DIR` - repository path on the VPS, for example `/home/ahmet/apps/videoflix-backend`

Repository secrets:

- `VPS_HOST` - VPS hostname or IP only (for example `203.0.113.10`), without `ssh`, username, or `user@host` syntax
- `VPS_SSH_PRIVATE_KEY` - private key dedicated to GitHub Actions deployment
- `VPS_KNOWN_HOSTS` - trusted SSH host-key line for the VPS

GitHub Environment:

- keep an environment named `production`
- restrict deployment branches/tags to `main`
- use the environment as the production deployment gate
- keep VPS credentials in repository secrets/variables rather than duplicating them as environment secrets/variables

Do not put the production `.env`, SSH private key, database password, SMTP password, or Django secret key in the repository.

## First production start

The normal automated deployment publishes an image and runs `scripts/deploy.sh`.

For a manual first start, set an image and run:

```bash
export APP_IMAGE=ghcr.io/<owner>/<repo>:latest
docker compose -f compose.prod.yaml up -d --wait
```

Check status and logs:

```bash
docker compose -f compose.prod.yaml ps
docker compose -f compose.prod.yaml logs --tail=100 web worker
```

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Django development server: `http://127.0.0.1:${APP_PORT} (8000 by default for the existing Videoflix VPS)`
- PostgreSQL: internal Docker network only
- Redis: internal Docker network only
- RQ worker: separate container

## CI locally

CI also runs Ruff and a Python dependency vulnerability audit on GitHub Actions:

```bash
python -m pip install -r requirements-ci.txt
ruff check .
pip-audit --strict -r requirements.txt
```

The same Docker test and Django deployment-check stack can be run locally:

```bash
docker compose -f compose.ci.yaml up --build --abort-on-container-exit --exit-code-from test
docker compose -f compose.ci.yaml down -v
```
