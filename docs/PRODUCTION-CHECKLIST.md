# Production Deployment Checklist

## Infrastructure

* [ ] PostgreSQL provisioned with automated backups.
* [ ] Redis configured with maxmemory and eviction policy.
* [ ] MinIO deployed with persistent volume and lifecycle rules.
* [ ] LiveKit server configured with valid API keys and public IP.
* [ ] NVIDIA GPU nodes have `nvidia-container-toolkit` installed.

## Security

* [ ] `.env` contains strong, randomly generated secrets.
* [ ] `Caddyfile` configured with a real domain for automatic HTTPS.
* [ ] CORS origins restricted to the real frontend domain.
* [ ] Rate limiting enabled on `/api/auth/login` and `/api/ai/process`.

## Application

* [ ] Alembic migrations run successfully.
* [ ] GPU Workers connect to Redis and MinIO successfully.
* [ ] Admin user seeded in database.
