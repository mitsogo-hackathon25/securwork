#!/usr/bin/env bash
# SecurWork — production deployment script
# Run on the VPS as root or with sudo after initial server setup.
set -euo pipefail

APP_DIR="/var/www/securwork"
BRANCH="${DEPLOY_BRANCH:-main}"

echo "==> Deploying SecurWork from branch: ${BRANCH}"

cd "${APP_DIR}"
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

echo "==> Backend: install dependencies"
cd "${APP_DIR}/backend"
source venv/bin/activate
pip install -r requirements.txt gunicorn

echo "==> Backend: migrate & collectstatic"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "==> Frontend: build"
cd "${APP_DIR}/frontend"
npm ci
npm run build

echo "==> Permissions"
chown -R www-data:www-data "${APP_DIR}"
chmod -R 755 "${APP_DIR}/backend/media"

echo "==> Restart services"
systemctl restart securwork
nginx -t && systemctl reload nginx

echo "==> Deploy complete. Verify: https://www.securwork.it"
