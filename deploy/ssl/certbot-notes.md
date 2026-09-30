# SSL Certificate Setup — Let's Encrypt

## Prerequisites

1. DNS A records for `securwork.it` and `www.securwork.it` point to VPS IP
2. Nginx is installed and `securwork.conf` is in place (HTTP block only initially)
3. Port 80 and 443 are open in firewall

## Initial Certificate (HTTP-only Nginx first)

If SSL blocks are not yet configured, use standalone or webroot method:

```bash
# Stop nginx temporarily for standalone (if no site config yet)
certbot certonly --standalone -d securwork.it -d www.securwork.it
```

Or with Nginx plugin (recommended once HTTP vhost exists):

```bash
certbot --nginx -d securwork.it -d www.securwork.it
```

Follow prompts:
- Enter email for renewal notices
- Agree to terms
- Choose redirect HTTP to HTTPS (recommended: yes)

## Certificate Location

```
/etc/letsencrypt/live/securwork.it/fullchain.pem
/etc/letsencrypt/live/securwork.it/privkey.pem
```

Referenced in `deploy/nginx/securwork.conf`.

## Auto-Renewal

Certbot installs a systemd timer. Verify:

```bash
systemctl status certbot.timer
certbot renew --dry-run
```

## Renewal Hook (optional)

Reload Nginx after renewal:

```bash
# /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
#!/bin/bash
systemctl reload nginx
```

```bash
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Connection refused` | Ensure Nginx listens on port 80 |
| `DNS problem` | Wait for DNS propagation |
| `Certificate not yet due` | Normal during dry-run |
| Mixed content after SSL | Update WP URLs to `https://` |
