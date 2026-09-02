#!/bin/bash
set -e

echo "[+] Waiting for PostgreSQL to be ready..."
while ! nc -z "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}"; do
  sleep 1
done
echo "[+] PostgreSQL is up and accepting connections!"

echo "[+] Waiting for Redis to be ready..."
while ! nc -z "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}"; do
  sleep 1
done
echo "[+] Redis is up!"

echo "[+] Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[+] Starting FastAPI server with Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2}
