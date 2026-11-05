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
    echo
    echo "If deploy failed during git update, check: git stash list"
    echo "Protected config backups are under /tmp/securwork-deploy-* until this script exits."
    exit 1
}

trap fail ERR

run_backend_compose() {
    local -a run_args=(run --rm --entrypoint python)
    if [ -f "${APP_DIR}/.env" ]; then
        run_args+=(-v "${APP_DIR}/.env:/app/.env:ro")
    fi
    docker compose "${run_args[@]}" backend "$@"
}

assert_production_frontend_compose() {
    local config_file="/tmp/securwork-compose-check.yml"
    if awk '/^  frontend:/ { found=1 } found && /^  [a-z]/ && !/^  frontend:/ { found=0 } found' "$config_file" \
        | grep -q 'node:20-alpine'; then
        echo
        echo "ERROR: docker-compose.yml is using the local DEV frontend (node + Vite)."
        echo "Production needs the nginx image built from ./frontend (see"
        echo "  deploy/docker-compose.production.yml)."
        echo "  cp deploy/docker-compose.production.yml docker-compose.yml"
        echo
        echo "Edit AFTER any 'git reset --hard origin/main' (reset overwrites this file):"
        echo "  nano ${APP_DIR}/docker-compose.yml"
        echo
        echo "If you have a known-good backup on this server, e.g.:"
        echo "  cp docker-compose.yml.pre-release docker-compose.yml"
        echo "Then run ./deploy/deploy.sh again."
        exit 1
    fi
}

wait_for_https() {
    local url="$1"
    local label="$2"
    local max_attempts="${3:-24}"
    local attempt=1
    while [ "$attempt" -le "$max_attempts" ]; do
        if curl -fsS -o /dev/null --max-time 15 "$url"; then
            echo "  ${label}: OK"
            return 0
        fi
        echo "  ${label}: not ready (attempt ${attempt}/${max_attempts}), waiting 5s..."
        sleep 5
        attempt=$((attempt + 1))
    done
    echo "  ${label}: failed after ${max_attempts} attempts"
    return 1
}

# Log smoke-test HTTP status; do not fail deploy (redirects / optional URLs).
smoke_check_url() {
    local url="$1"
    local label="$2"
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$url" 2>/dev/null || echo "000")"
    case "$code" in
        2*|3*)
            echo "  ${label}: HTTP ${code} OK"
            ;;
        404)
            echo "  ${label}: HTTP 404 (optional asset missing — deploy continues)"
            ;;
        *)
            echo "  WARNING: ${label}: HTTP ${code}"
            ;;
    esac
}

# Older protected settings.py backups omit these; without them SECURE_SSL_REDIRECT causes 301 on /api/.
ensure_production_proxy_ssl_settings() {
    local settings="backend/config/settings.py"
    if grep -q 'SECURE_PROXY_SSL_HEADER' "$settings"; then
        echo "  settings.py: SECURE_PROXY_SSL_HEADER present"
        return 0
    fi
    echo "  settings.py: patching SECURE_PROXY_SSL_HEADER + USE_X_FORWARDED_HOST..."
    python3 <<'PY'
import pathlib
import sys

path = pathlib.Path("backend/config/settings.py")
text = path.read_text()
needle = 'SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)'
block = """SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    # TLS terminates at host nginx / load balancer; backend sees HTTP from Docker proxy.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = config("USE_X_FORWARDED_HOST", default=True, cast=bool)"""
if needle not in text:
    print("ERROR: could not find SECURE_SSL_REDIRECT in settings.py", file=sys.stderr)
    sys.exit(1)
if "SECURE_PROXY_SSL_HEADER" in text:
    sys.exit(0)
path.write_text(text.replace(needle, block, 1))
PY
}

ensure_frontend_nginx_proxy_headers() {
    local nginx="frontend/nginx.conf"
    if grep -q 'X-Forwarded-Proto https' "$nginx"; then
        echo "  frontend/nginx.conf: X-Forwarded-Proto https present"
        return 0
    fi
    echo "  frontend/nginx.conf: adding X-Forwarded-Proto https to API/media/django-admin proxies..."
    python3 <<'PY'
import pathlib
import re
import sys

path = pathlib.Path("frontend/nginx.conf")
text = path.read_text()
if "X-Forwarded-Proto https" in text:
    sys.exit(0)

def add_proto(block: str) -> str:
    if "X-Forwarded-Proto" in block:
        return block
    return re.sub(
        r"(proxy_set_header Host \$host;\n)",
        r"\1        proxy_set_header X-Forwarded-Proto https;\n",
        block,
        count=1,
    )

text = re.sub(
    r"location /(?:api/|media/|django-admin/) \{.*?\n    \}",
    lambda m: add_proto(m.group(0)),
    text,
    flags=re.DOTALL,
)
if "X-Forwarded-Proto https" not in text:
    print("ERROR: could not patch frontend/nginx.conf", file=sys.stderr)
    sys.exit(1)
path.write_text(text)
PY
}

echo "[1/11] Checking Git repository..."
git status --short
echo

echo "[2/11] Saving production configuration..."

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

echo "[3/11] Checking remote Git state..."
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
    echo "Updating application to origin/$BRANCH (reset — server app code should match Git)..."

    git reset --hard "origin/${BRANCH}"

    echo
    echo "Restoring production configuration from pre-deploy backup..."

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

echo "[4/11] Verifying protected production configuration..."

test -f backend/config/settings.py
test -f docker-compose.yml
test -f frontend/nginx.conf

grep -q "ALLOWED_HOSTS" backend/config/settings.py
grep -q "DB_HOST=db" .env
grep -q "proxy_pass http://backend:8000" frontend/nginx.conf

echo "Ensuring HTTPS proxy settings (admin login / API POST)..."
ensure_production_proxy_ssl_settings
ensure_frontend_nginx_proxy_headers
grep -q 'SECURE_PROXY_SSL_HEADER' backend/config/settings.py
grep -q 'X-Forwarded-Proto https' frontend/nginx.conf

echo "Production configuration looks valid."
echo

echo "[5/11] Validating Docker Compose configuration..."

if ! docker compose config >/tmp/securwork-compose-check.yml 2>/tmp/securwork-compose-config.err; then
    echo
    cat /tmp/securwork-compose-config.err
    echo
    echo "ERROR: docker-compose.yml is invalid or incomplete."
    echo "Restore the production template (valid YAML with services.frontend):"
    echo "  cp ${APP_DIR}/deploy/docker-compose.production.yml ${APP_DIR}/docker-compose.yml"
    echo "Adjust ports if needed, then run ./deploy/deploy.sh again."
    exit 1
fi
assert_production_frontend_compose

echo "Docker Compose configuration: OK"
echo

echo "[6/11] Building frontend static assets (npm)..."

cd "${APP_DIR}/frontend"
if command -v npm >/dev/null 2>&1; then
    npm ci
    npm run build
else
    echo "  WARNING: npm not on host — relying on Docker frontend image build only."
fi
cd "${APP_DIR}"
echo

echo "[7/11] Building application images..."

export GIT_COMMIT="$(git rev-parse HEAD)"
docker compose build --build-arg "GIT_COMMIT=${GIT_COMMIT}" backend frontend

echo "Docker images built successfully."
echo

echo "[8/11] Running database migrations..."

run_backend_compose manage.py migrate --noinput

echo "Database migrations completed."
echo

echo "[9/11] Collecting static files..."

run_backend_compose manage.py collectstatic --noinput

echo "Static files collected."
echo

echo "[10/11] Running Django production checks..."

run_backend_compose manage.py check --deploy

echo
echo "Django production checks completed."
echo

echo "Starting updated application..."

docker compose up -d backend frontend

echo "Application containers started."
echo

echo "Waiting for services (frontend build / nginx may take up to 2 minutes)..."

sleep 5

echo
docker compose ps

echo

echo "[11/11] Running production smoke tests..."

echo "Testing homepage..."
wait_for_https "https://www.securwork.it/" "Homepage"

echo "Testing API..."
smoke_check_url "https://www.securwork.it/api/" "API"

echo "Testing admin login API (must not redirect POST with 301)..."
login_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -X POST \
    'https://www.securwork.it/api/auth/login/?lang=en' \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"__deploy_smoke_invalid__"}' 2>/dev/null || echo "000")"
case "$login_code" in
    301)
        echo "  WARNING: POST /api/auth/login/ returned 301 — check SECURE_PROXY_SSL_HEADER and nginx X-Forwarded-Proto"
        ;;
    401|400)
        echo "  Admin login API: HTTP ${login_code} (SSL/proxy OK; use real ADMIN_PASSWORD to sign in)"
        ;;
    200)
        echo "  Admin login API: HTTP 200"
        ;;
    *)
        echo "  WARNING: Admin login API: HTTP ${login_code}"
        ;;
esac

echo "Testing React admin..."
smoke_check_url "https://www.securwork.it/admin/" "React admin"

echo "Testing Django admin..."
smoke_check_url "https://www.securwork.it/django-admin/" "Django admin"

echo "Testing media..."
smoke_check_url "https://www.securwork.it/media/products/sw-dv-003.jpg" "Media sample"

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
