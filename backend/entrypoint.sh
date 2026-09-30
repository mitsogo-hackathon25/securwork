#!/bin/bash
set -e

echo "==> Waiting for database..."
python << END
import time, os
import psycopg2
for i in range(30):
    try:
        psycopg2.connect(
            dbname=os.environ.get("DB_NAME", "securwork"),
            user=os.environ.get("DB_USER", "securwork"),
            password=os.environ.get("DB_PASSWORD", "securwork"),
            host=os.environ.get("DB_HOST", "db"),
        ).close()
        break
    except psycopg2.OperationalError:
        time.sleep(1)
else:
    raise SystemExit("Database not available")
END

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

if [ "${SEED_DATA:-true}" = "true" ]; then
    echo "==> Seeding data..."
    python manage.py seed_data --admin-password="${ADMIN_PASSWORD:-SecurWork_Admin_2026!}" 2>/dev/null || true
    python manage.py seed_catalog 2>/dev/null || true
fi

echo "==> Starting server..."
exec "$@"
