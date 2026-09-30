# SecurWork — DNS Configuration (Aruba → Hostinger VPS)

The domain **securwork.it** is registered with **Aruba**. The website is hosted on **Hostinger KVM 1 VPS**.

**Do not transfer the domain** unless explicitly requested. Only update DNS records.

## Overview

```
Visitor → securwork.it (Aruba DNS) → A record → Hostinger VPS IP → Nginx → Django API + React SPA
```

## Step 1 — Get Your VPS IP Address

From Hostinger panel (hPanel → VPS → your server):

Note the **public IPv4 address**, e.g. `123.45.67.89`.

## Step 2 — Log Into Aruba DNS Panel

1. Go to [https://www.aruba.it](https://www.aruba.it)
2. Log in to your Aruba account
3. Navigate to **Domini** → **securwork.it** → **Gestione DNS** / **DNS Management**

## Step 3 — Configure DNS Records

Remove or update any conflicting A/CNAME records for `@` and `www`.

### Required records

| Type | Host / Name | Value | TTL |
|------|-------------|-------|-----|
| A | `@` (or blank) | `YOUR_VPS_IP` | 3600 |
| A | `www` | `YOUR_VPS_IP` | 3600 |

**Alternative for www** (if Aruba supports CNAME for www):

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | `@` | `YOUR_VPS_IP` | 3600 |
| CNAME | `www` | `securwork.it` | 3600 |

### Optional records (email — only if using Aruba mail)

If the client uses Aruba email (`info@securwork.it`), **do not remove MX records**. Add only the A records above without touching existing MX/SPF/DKIM records for email.

| Type | Host | Value | Notes |
|------|------|-------|-------|
| MX | `@` | (existing Aruba MX) | Keep if email stays at Aruba |
| TXT | `@` | (existing SPF) | Keep for email deliverability |

## Step 4 — Propagation

DNS changes can take **15 minutes to 48 hours** to propagate globally.

Check propagation:

```bash
dig securwork.it A +short
dig www.securwork.it A +short
```

Or use: [https://www.whatsmydns.net](https://www.whatsmydns.net)

Both should return your Hostinger VPS IP.

## Step 5 — Verify Site URL

After DNS propagates and SSL is installed, confirm these environment variables in `/var/www/securwork/.env`:

```env
FRONTEND_URL=https://www.securwork.it
ALLOWED_HOSTS=www.securwork.it,securwork.it
CORS_ALLOWED_ORIGINS=https://www.securwork.it
```

Then restart the backend:

```bash
systemctl restart securwork
```

## Step 6 — SSL Certificate

Once DNS points to the VPS, run Certbot (see [DEPLOYMENT.md](DEPLOYMENT.md)):

```bash
certbot --nginx -d securwork.it -d www.securwork.it
```

## Redirect: non-www → www (recommended)

The Nginx config in `deploy/nginx/securwork.conf` redirects `securwork.it` → `www.securwork.it` for consistency.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Site not loading | Wait for DNS propagation; verify A records |
| SSL certificate fails | DNS must resolve to VPS before running certbot |
| www works but apex doesn't | Ensure A record for `@` is set |
| Email stops working | Restore MX records; A records don't affect email if MX unchanged |
| Mixed content warnings | Ensure `FRONTEND_URL` uses `https://` |
| API CORS errors | Check `CORS_ALLOWED_ORIGINS` matches `https://www.securwork.it` |
| Old site still showing | Clear browser cache; check TTL; flush local DNS |

## Hostinger Panel (Optional)

If using Hostinger's DNS instead of Aruba (not recommended unless nameservers are changed):

1. Hostinger hPanel → **DNS / Nameservers**
2. Only change nameservers at Aruba if migrating DNS entirely to Hostinger

**Default approach:** Keep domain at Aruba, point A records to Hostinger VPS.
