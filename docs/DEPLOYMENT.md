# SecurWork — Production Deployment (Django + React)

Target: **Hostinger KVM 1 VPS** · Ubuntu 24.04 LTS · Nginx · Gunicorn · PostgreSQL 16

## 1. Server Setup

```bash
apt update && apt upgrade -y
apt install -y nginx postgresql postgresql-contrib python3-pip python3-venv \
  certbot python3-certbot-nginx git ufw fail2ban nodejs npm
```

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

## 2. PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE securwork;
CREATE USER securwork WITH PASSWORD 'STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE securwork TO securwork;
\q
```

## 3. Deploy Application

```bash
mkdir -p /var/www/securwork
cd /var/www/securwork
git clone YOUR_REPO_URL .
```

### Environment

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```env
DEBUG=false
SECRET_KEY=long-random-secret
ALLOWED_HOSTS=www.securwork.it,securwork.it
DB_HOST=localhost
DB_NAME=securwork
DB_USER=securwork
DB_PASSWORD=strong-password
CORS_ALLOWED_ORIGINS=https://www.securwork.it
FRONTEND_URL=https://www.securwork.it
SECURE_SSL_REDIRECT=true
SEED_DATA=false

# Email (SMTP — required for contact form & order emails)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@securwork.it
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=true
CONTACT_EMAIL=info@securwork.it
DEFAULT_FROM_EMAIL=noreply@securwork.it

# Stripe (live keys)
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Company info (shown on contact page & footer)
SECURWORK_COMPANY_NAME=SecurWork S.r.l.
SECURWORK_COMPANY_VAT=IT00000000000
SECURWORK_COMPANY_ADDRESS=Via Esempio 1
SECURWORK_COMPANY_CITY=20100 Milano, Italia
SECURWORK_COMPANY_PHONE=+39 02 0000000
SECURWORK_MAP_LAT=45.4642
SECURWORK_MAP_LNG=9.1900
```

### Backend

```bash
cd /var/www/securwork/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data          # first deploy only
python manage.py seed_catalog       # first deploy only (demo products)
python manage.py createsuperuser
```

### Gunicorn systemd service

```bash
cp /var/www/securwork/deploy/systemd/securwork.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable securwork
systemctl start securwork
systemctl status securwork
```

### Frontend build

```bash
cd /var/www/securwork/frontend
npm ci
npm run build
# Output: frontend/dist/
```

## 4. Nginx

```bash
cp /var/www/securwork/deploy/nginx/securwork.conf /etc/nginx/sites-available/securwork
ln -s /etc/nginx/sites-available/securwork /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

## 5. SSL

DNS must point to VPS first (see [DNS-SETUP.md](DNS-SETUP.md)).

```bash
certbot --nginx -d securwork.it -d www.securwork.it
certbot renew --dry-run
```

## 6. File Permissions

```bash
chown -R www-data:www-data /var/www/securwork
chmod -R 755 /var/www/securwork/backend/media
```

## 7. Stripe Webhook

In the Stripe Dashboard:

1. **Developers → Webhooks → Add endpoint**
2. URL: `https://www.securwork.it/api/payments/webhook/stripe/`
3. Events: `checkout.session.completed`, `checkout.session.expired`
4. Copy signing secret to `STRIPE_WEBHOOK_SECRET` in `.env`
5. Restart: `systemctl restart securwork`

## 8. Backups

```bash
chmod +x /var/www/securwork/deploy/scripts/backup.sh
# Add to crontab (daily at 3am):
# 0 3 * * * /var/www/securwork/deploy/scripts/backup.sh >> /var/log/securwork-backup.log 2>&1
```

See [MAINTENANCE.md](MAINTENANCE.md) for update and backup procedures.

## 9. Subsequent Deploys

```bash
chmod +x /var/www/securwork/deploy/scripts/deploy.sh
/var/www/securwork/deploy/scripts/deploy.sh
```

## 10. Post-Deployment Checklist

- [ ] https://www.securwork.it loads React storefront
- [ ] https://www.securwork.it/api/products/ returns JSON
- [ ] https://www.securwork.it/sitemap.xml returns XML
- [ ] https://www.securwork.it/admin/login — React product admin
- [ ] https://www.securwork.it/django-admin/ — Django admin (orders, CMS, etc.)
- [ ] Nginx config updated: `/admin/` → React SPA, `/django-admin/` → Django
- [ ] Admin password changed from default
- [ ] `DEBUG=false` in production `.env`
- [ ] Contact form sends email (test submission)
- [ ] Stripe test/live payment completes end-to-end
- [ ] Cookie banner appears on first visit
- [ ] Backups scheduled
- [ ] CMS legal pages reviewed by lawyer
- [ ] Replace demo products with real catalog
