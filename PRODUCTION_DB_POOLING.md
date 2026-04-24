# Production Postgres + PgBouncer Runbook

This runbook is for stable production startup and operations of PostgreSQL + PgBouncer.

## 1) Required environment variables

Set these in your production `.env` (do not use defaults in production):

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `APP_DB_USER`
- `APP_DB_PASSWORD`
- `PGBOUNCER_DB_USER`
- `PGBOUNCER_DB_PASSWORD`
- `PGBOUNCER_DB_NAME` (typically same as `POSTGRES_DB`)
- `DATABASE_URL` (pointing at pgbouncer)
- `CELERY_BROKER_URL`
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`
- `SECRET_KEY`
- `ALLOWED_HOSTS`

Example `DATABASE_URL`:

`postgres://APP_DB_USER:APP_DB_PASSWORD@pgbouncer:5432/POSTGRES_DB`

## 2) Start stack

From `server/`:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

## 3) Verify health

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 db pgbouncer
```

Expected:
- `db` is `healthy`
- `pgbouncer` is `Up`
- `pgbouncer` logs show `process up: PgBouncer`

## 4) Safe migration flow

Run migrations through the app container (it connects via PgBouncer):

```bash
docker compose -f docker-compose.prod.yml exec -T api poetry run python manage.py migrate
```

## 5) PgBouncer tuning knobs

Use these env vars to tune pooling without editing compose:

- `PGBOUNCER_POOL_MODE` (default: `transaction`)
- `PGBOUNCER_MAX_CLIENT_CONN` (default: `500`)
- `PGBOUNCER_DEFAULT_POOL_SIZE` (default: `20`)
- `PGBOUNCER_RESERVE_POOL_SIZE` (default: `5`)
- `PGBOUNCER_RESERVE_POOL_TIMEOUT` (default: `5`)
- `PGBOUNCER_SERVER_IDLE_TIMEOUT` (default: `300`)

## 6) Troubleshooting

### `wrong password type`
Set `PGBOUNCER_AUTH_TYPE=scram-sha-256` and ensure Postgres user passwords are SCRAM.

### `no such database`
Set `PGBOUNCER_DB_NAME` to your production DB name. For tests only, use wildcard (`*`).

### architecture `exec format error`
Re-pull images for your host architecture and recreate containers.
