# Videoflix Backend

Videoflix is a Django REST Framework backend for a video streaming application.

I implemented the backend architecture and application logic, including authentication, email activation and password recovery, PostgreSQL persistence, Redis caching, asynchronous background processing with Django RQ, FFmpeg-based video transcoding, thumbnail generation, and authenticated HLS streaming in multiple resolutions.

> **Frontend:** The frontend used as the client interface was provided by Developer Akademie and is maintained separately:
> [Developer Akademie – project.Videoflix](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix)

---

## Quick Start

### 1. Clone the repository

```bash
git clone <YOUR_BACKEND_REPOSITORY_URL>
cd videoflix-backend
```

### 2. Create the environment file

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the required values in `.env` using `.env.example` as the source of truth for all available environment variables.

Never commit the real `.env` file or production credentials.

### 3. Start the application

```bash
docker compose up --build
```

The backend API is available at:

```text
http://127.0.0.1:8000/api/
```

The Django administration interface is available at:

```text
http://127.0.0.1:8000/admin/
```

### 4. Run the test suite

```bash
docker compose exec web python manage.py test
```

---

## Features

### Authentication & Account Management

- User registration with email and password
- Inactive accounts until email activation
- Email-based account activation
- Login using email and password
- JWT authentication with HttpOnly cookies
- Access and refresh tokens
- Access-token refresh flow
- Refresh-token blacklisting on logout
- Password reset via email
- Token-based password confirmation
- Generic authentication responses where appropriate to reduce account enumeration

### Video Management

- Video upload through Django Admin
- Processing status tracking:
  - `pending`
  - `processing`
  - `ready`
  - `failed`
- Only successfully processed videos are exposed through the video catalogue
- Videos are returned newest first using `created_at DESC`

### Video Processing

- Asynchronous video processing with Django RQ
- Redis-backed task queue
- FFmpeg-based transcoding
- Automatic thumbnail generation
- HLS output in:
  - `480p`
  - `720p`
  - `1080p`
- HLS manifests (`.m3u8`)
- HLS transport stream segments (`.ts`)
- Failed processing jobs update the video status accordingly

### Streaming

Authenticated users can access:

- the video catalogue
- generated thumbnails
- HLS manifests
- HLS video segments

Streaming endpoints are protected by JWT authentication.

### Redis Caching

Redis is used as a Django caching layer for the video catalogue.

The video list is cached after retrieval and automatically invalidated when video data changes, ensuring that clients receive fresh catalogue data without unnecessary database queries.

### Email Delivery

The backend supports real SMTP delivery for:

- account activation
- password reset

Emails are available as HTML and plain-text alternatives.

SMTP credentials and sender configuration are stored through environment variables.

---

## Technology Stack

### Backend

- Python 3.12
- Django 6.1
- Django REST Framework
- PostgreSQL

### Authentication & Security

- Simple JWT
- HttpOnly cookies
- Refresh-token blacklist
- Django password hashing and validation
- CORS configuration
- CSRF trusted origins
- Environment-based secrets

### Processing & Infrastructure

- Redis
- django-redis
- Django RQ
- FFmpeg
- Gunicorn
- WhiteNoise
- Docker
- Docker Compose

### Testing

- Django Test Framework
- Django REST Framework `APITestCase`
- Coverage.py
- `unittest.mock`

---

## Architecture

```text
Frontend
   │
   │ REST API / HttpOnly JWT Cookies
   ▼
Django REST Framework
   │
   ├── Users
   │   ├── Registration
   │   ├── Email Activation
   │   ├── Login / Logout
   │   ├── Token Refresh
   │   └── Password Reset
   │
   ├── Videos
   │   ├── Catalogue API
   │   ├── Redis Cache
   │   └── Authenticated HLS Streaming
   │
   ▼
PostgreSQL
```

### Video Processing Pipeline

```text
Video Upload
    │
    ▼
Django Admin
    │
    ▼
post_save Signal
    │
    ▼
Django RQ
    │
    ▼
Redis Queue
    │
    ▼
Background Worker
    │
    ▼
FFmpeg
    ├── Thumbnail
    ├── 480p HLS
    ├── 720p HLS
    └── 1080p HLS
    │
    ▼
Processing Status: READY
    │
    ▼
Available through the REST API
```

### Video Catalogue Cache

```text
GET /api/video/
      │
      ▼
Redis Cache
   │       │
 HIT      MISS
   │       │
   │       ▼
   │   PostgreSQL
   │       │
   │       ▼
   │   Cache Result
   │       │
   └───────┘
      │
      ▼
   Response
```

When a video is created, changed, or deleted, the cached catalogue is invalidated automatically.

---

## API Overview

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/register/` | Register a new inactive user |
| `GET` | `/api/activate/<uidb64>/<token>/` | Activate an account |
| `POST` | `/api/login/` | Authenticate and set JWT cookies |
| `POST` | `/api/logout/` | Logout and invalidate the refresh token |
| `POST` | `/api/token/refresh/` | Create a new access token |
| `POST` | `/api/password_reset/` | Request a password-reset email |
| `POST` | `/api/password_confirm/<uidb64>/<token>/` | Set a new password |

### Videos

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/video/` | Retrieve all ready videos |
| `GET` | `/api/video/<movie_id>/thumbnail/` | Retrieve an authenticated thumbnail |
| `GET` | `/api/video/<movie_id>/<resolution>/index.m3u8` | Retrieve an HLS manifest |
| `GET` | `/api/video/<movie_id>/<resolution>/<segment>/` | Retrieve an HLS segment |

The video endpoints require authentication.

Supported streaming resolutions:

```text
480p
720p
1080p
```

---

## Authentication Flow

### Registration

```text
Registration
    ↓
Inactive User
    ↓
Activation Email
    ↓
Activation Link
    ↓
Account Activated
    ↓
Login Available
```

### Login

After successful authentication, the backend stores:

```text
access_token
refresh_token
```

as HttpOnly cookies.

The access token protects API requests. The refresh token can be used to create a new access token.

### Logout

On logout:

- the refresh token is blacklisted
- authentication cookies are deleted
- the blacklisted refresh token can no longer be used

### Password Reset

```text
Password Reset Request
        ↓
Generic API Response
        ↓
Reset Email
        ↓
UID + Token
        ↓
New Password
        ↓
Password Updated
```

The reset request returns the same public response whether or not an email address exists.

---

## Testing & Coverage

Run all automated tests:

```bash
docker compose exec web python manage.py test
```

Current project status:

```text
25 automated tests
All tests passing
Coverage is measured with Coverage.py and can be generated locally with the commands below.
```

Generate a coverage report:

```bash
docker compose exec web coverage run manage.py test
docker compose exec web coverage report -m
```

The automated test suite covers areas including:

- user registration
- account activation
- activation email generation
- active and inactive login behavior
- JWT cookie creation
- token refresh
- logout and refresh-token invalidation
- password-reset emails
- password confirmation
- authenticated and unauthenticated video access
- authenticated thumbnail delivery
- ready-video filtering
- newest-first video ordering
- Redis caching
- automatic cache invalidation
- authenticated HLS manifests
- authenticated HLS segments
- invalid HLS resolutions
- unknown video requests
- successful background video processing
- failed FFmpeg processing
- processing-status transitions

The video-processing task module currently reaches 100% statement coverage.

---

## Environment Variables

The application reads sensitive and environment-specific configuration from `.env`.

Important categories include:

- Django secret key and debug mode
- allowed hosts and trusted origins
- frontend URL
- PostgreSQL credentials
- Redis configuration
- SMTP server and credentials
- default email sender

The real `.env` file must remain outside version control.

Use `.env.example` as the configuration template.

---

## Security

The backend includes several security measures:

- Django password hashing
- Django password validation
- JWT authentication
- HttpOnly authentication cookies
- configurable Secure and SameSite cookie settings
- refresh-token blacklisting
- global authenticated-by-default DRF permissions
- explicitly public authentication/account endpoints
- protected video, thumbnail, and HLS endpoints
- generic responses for sensitive account flows
- server-side validation of HLS segment paths
- environment variables for secrets and credentials
- environment-driven CORS restrictions
- secure session and CSRF cookies when `DEBUG=False`
- reverse-proxy HTTPS awareness
- CSRF trusted-origin configuration
- inactive accounts until email verification

Production deployments should use HTTPS, `DEBUG=False`, production-specific allowed hosts, trusted origins, secure cookies, and protected production credentials.

---

## Development Notes

- Uploaded source videos, generated thumbnails, and HLS files should remain outside version control.
- Redis is used both for background job processing and application caching.
- PostgreSQL is used as the application database.
- Video processing runs asynchronously so FFmpeg work does not block normal API requests.
- The API and frontend are maintained as separate applications.
- `.m3u8` manifests and `.ts` segments are served only for authenticated users.
- The provided frontend is used to demonstrate and interact with this backend implementation.

---

## Production Deployment

Production-specific configuration is documented in
[`DEPLOYMENT.md`](DEPLOYMENT.md).

The repository also contains `.env.production.example` with non-secret example
values for an `ahmet-balci.de` / `api.ahmet-balci.de` deployment.

Important production principles:

- keep `DEBUG=False`
- keep the real `.env` outside version control
- use HTTPS through a reverse proxy
- do not expose PostgreSQL, Redis, or port `8000` publicly
- do not expose the complete `/media/` directory directly
- run `python manage.py check --deploy` before going live


## Frontend Repository

The client interface used with this backend is available here:

[Developer Akademie – project.Videoflix](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix)
