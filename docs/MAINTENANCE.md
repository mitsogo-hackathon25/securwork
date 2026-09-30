# SecurWork — Maintenance Guide

## Weekly

- Review new orders in Django Admin → Orders
- Check low-stock variants in Store → Product variants
- Review contact form submissions

## Monthly

- Update system packages: `apt update && apt upgrade`
- Update Python dependencies in `backend/requirements.txt`
- Update npm packages in `frontend/package.json`
- Test backup restore
- Verify SSL auto-renewal: `certbot renew --dry-run`

## Backups

### Database

```bash
pg_dump -U securwork securwork | gzip > /backups/securwork-$(date +%Y%m%d).sql.gz
```

### Media files

```bash
tar -czf /backups/media-$(date +%Y%m%d).tar.gz /var/www/securwork/backend/media/
```

### Automated cron

```bash
0 3 * * * /var/www/securwork/deploy/scripts/backup.sh >> /var/log/securwork-backup.log 2>&1
```

## Updates

```bash
cd /var/www/securwork
git pull

# Backend
cd backend && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart securwork

# Frontend
cd ../frontend
npm install && npm run build
```

## Logs

| Log | Location |
|-----|----------|
| Gunicorn | `journalctl -u securwork -f` |
| Nginx | `/var/log/nginx/error.log` |
| PostgreSQL | `/var/log/postgresql/` |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API 502 | `systemctl status securwork` — restart service |
| Static files missing | `python manage.py collectstatic --noinput` |
| DB connection error | Check `.env` and PostgreSQL status |
| Frontend blank page | Rebuild: `cd frontend && npm run build` |
| CORS errors | Update `CORS_ALLOWED_ORIGINS` in `.env` |
