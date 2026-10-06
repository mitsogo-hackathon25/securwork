#!/usr/bin/env bash

set -Eeuo pipefail

APP_DIR="/opt/securwork/securwork"
BRANCH="main"

PROTECTED_FILES=(
    "backend/config/settings.py"
    "docker-compose.yml"
    "frontend/nginx.conf"
)

BACKUP_DIR="/tmp/securwork-deploy-$(date +%Y%m%d-%H%M%S)"
STASH_NAME="securwork-production-config-$(date +%Y%m%d-%H%M%S)"

cd "$APP_DIR"

echo "========================================"
echo " SecurWork Production Deployment"
echo "========================================"
echo "Started: $(date)"
echo

cleanup() {
    rm -rf "$BACKUP_DIR"
}

trap cleanup EXIT

fail() {
    echo
    echo "========================================"
    echo " DEPLOYMENT FAILED"
    echo "========================================"
    echo "Failed command: $BASH_COMMAND"
    echo
    echo "Check the output above and container logs with:"
    echo "  docker compose logs --tail=100 backend"
    echo "  docker compose logs --tail=100 frontend"
    exit 1
}

trap fail ERR

echo "[1/10] Checking Git repository..."
git status --short
echo

echo "[2/10] Saving production configuration..."

mkdir -p "$BACKUP_DIR"

for file in "${PROTECTED_FILES[@]}"; do
    if [ -f "$file" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp -a "$file" "$BACKUP_DIR/$file"
        echo "  Saved: $file"
    else
        echo "  WARNING: $file does not exist"
    fi
done

echo

echo "[3/10] Checking remote Git state..."
git fetch origin

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "origin/$BRANCH")"

echo "  Current commit: $LOCAL_COMMIT"
echo "  Remote commit:  $REMOTE_COMMIT"
echo

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then

    echo "Production configuration files are protected."

    echo
    echo "Temporarily stashing protected production files..."

    git stash push \
        -m "$STASH_NAME" \
        -- \
        "${PROTECTED_FILES[@]}" >/dev/null

    echo "Protected files stashed."

    echo
    echo "Updating application from origin/$BRANCH..."

    git pull --ff-only origin "$BRANCH"

    echo
    echo "Restoring production configuration..."

    for file in "${PROTECTED_FILES[@]}"; do
        if [ -f "$BACKUP_DIR/$file" ]; then
            cp -a "$BACKUP_DIR/$file" "$file"
            echo "  Restored: $file"
        fi
    done

    echo

    STASH_REF="$(git stash list --format='%gd %s' | grep "$STASH_NAME" | head -1 | awk '{print $1}' || true)"

    if [ -n "$STASH_REF" ]; then
        git stash drop "$STASH_REF" >/dev/null
        echo "Temporary Git stash removed."
    fi

else
    echo "Already at latest origin/$BRANCH."
fi

echo

echo "[4/10] Verifying protected production configuration..."

test -f backend/config/settings.py
test -f docker-compose.yml
test -f frontend/nginx.conf

grep -q "ALLOWED_HOSTS" backend/config/settings.py
grep -q "DB_HOST=db" .env
grep -q "proxy_pass http://backend:8000" frontend/nginx.conf

echo "Production configuration looks valid."
echo

echo "[5/10] Validating Docker Compose configuration..."

docker compose config >/tmp/securwork-compose-check.yml

echo "Docker Compose configuration: OK"
echo

echo "[6/10] Building application images..."

docker compose build backend frontend

echo "Docker images built successfully."
echo

echo "[7/10] Running database migrations..."

docker compose run --rm backend python manage.py migrate --noinput

echo "Database migrations completed."
echo

echo "[8/10] Collecting static files..."

docker compose run --rm backend python manage.py collectstatic --noinput

echo "Static files collected."
echo

echo "[9/10] Running Django production checks..."

docker compose run --rm backend python manage.py check --deploy

echo
echo "Django production checks completed."
echo

echo "Starting updated application..."

docker compose up -d backend frontend

echo "Application containers started."
echo

echo "Waiting for containers..."

sleep 8

echo
docker compose ps

echo

echo "[10/10] Running production smoke tests..."

echo "Testing homepage..."
curl -fsS -o /dev/null \
    --max-time 20 \
    https://www.securwork.it/

echo "  Homepage: OK"

echo "Testing API..."
curl -fsS \
    --max-time 20 \
    https://www.securwork.it/api/ \
    -o /tmp/securwork-api-response.json

echo "  API: OK"

echo "Testing React admin..."
curl -fsS -o /dev/null \
    --max-time 20 \
    https://www.securwork.it/admin/

echo "  React admin: OK"

echo "Testing Django admin..."
ADMIN_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' \
    --max-time 20 \
    https://www.securwork.it/django-admin/)"

if [ "$ADMIN_STATUS" != "200" ] && [ "$ADMIN_STATUS" != "302" ]; then
    echo "Django admin returned HTTP $ADMIN_STATUS"
    exit 1
fi

echo "  Django admin: HTTP $ADMIN_STATUS"

echo "Testing media..."
MEDIA_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' \
    --max-time 20 \
    https://www.securwork.it/media/products/sw-dv-003.jpg)"

if [ "$MEDIA_STATUS" != "200" ]; then
    echo "Media returned HTTP $MEDIA_STATUS"
    exit 1
fi

echo "  Media: HTTP 200"

echo
echo "Checking backend container..."

docker compose ps backend | grep -q "Up"

echo "  Backend container: UP"

echo
echo "Checking frontend container..."

docker compose ps frontend | grep -q "Up"

echo "  Frontend container: UP"

echo
echo "========================================"
echo " DEPLOYMENT SUCCESSFUL"
echo "========================================"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Finished: $(date)"
echo
echo "Application:"
echo "  https://www.securwork.it/"
echo
echo "React Admin:"
echo "  https://www.securwork.it/admin/"
echo
echo "Django Admin:"
echo "  https://www.securwork.it/django-admin/"
echo
