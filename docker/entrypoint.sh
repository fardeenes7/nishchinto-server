#!/bin/sh
set -e

echo "──────────────────────────────────────────────────────"
echo "  Nishchinto Backend — Container Startup"
echo "──────────────────────────────────────────────────────"

echo "⏳ Running database migrations..."
python manage.py migrate --noinput

echo "⏳ Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Startup complete. Launching: $@"
exec "$@"
