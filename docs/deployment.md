# Deployment

## Target
- **Frontend**: Vercel (`apps/web`)
- **Backend**: single VPS with Docker Compose (`docker/docker-compose.prod.yml`)

## Backend services
- `api`: FastAPI
- `worker`: Celery worker
- `beat`: Celery Beat scheduler
- `postgres`: Postgres 16
- `redis`: Redis 7
- `flower`: Celery monitoring

## Environment variables
Copy `.env.example` to `.env` and fill in at minimum:
- `DATABASE_URL`, `ALEMBIC_DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH`
- `GEMINI_API_KEY`

## Runbook (prod)
On the VPS:
- Build and start: `docker compose -f docker/docker-compose.prod.yml up --build -d`
- Run migrations: `docker compose -f docker/docker-compose.prod.yml exec api alembic upgrade head`
- Check health: `curl http://<host>:8000/health`

## Vercel
Set `NEXT_PUBLIC_API_URL` to the backend base URL (e.g. `https://api.yourdomain.tld`).

