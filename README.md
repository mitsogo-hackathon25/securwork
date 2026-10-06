# SecurWork — Bilingual Workwear E-Commerce

Professional workwear and occupational clothing store for the Italian market.

- **Domain:** [https://www.securwork.it](https://www.securwork.it)
- **Stack:** Django · Django REST Framework · React · PostgreSQL
- **Deployment:** Hostinger KVM 1 VPS (Ubuntu · Nginx · Gunicorn · PostgreSQL)

## Architecture

```
securwork/
├── backend/          # Django API + Admin panel
│   ├── store/        # Products, categories, variants
│   ├── orders/       # Cart, checkout, orders
│   ├── accounts/     # User auth (JWT)
│   └── cms/          # Pages, FAQ, contact
├── frontend/         # React SPA (Vite + TypeScript)
├── deploy/           # Nginx, SSL, backup scripts
├── docs/             # Deployment, handover, maintenance
└── content-seed/     # Category/product seed data
```

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

### 1. Configure environment

```bash
cp .env.example .env
cp docker-compose.override.example.yml docker-compose.override.yml
# Edit .env with strong passwords (use local dev block for Docker on your machine)
```

### 2. Start all services

```bash
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| **Storefront** | http://localhost:5180 |
| **API** | http://localhost:8000/api/ |
| **Product admin** (React) | http://localhost:5180/admin/login |
| **Django admin** | http://localhost:5180/django-admin/ |

### 3. Admin credentials

- **Username:** `admin`
- **Password:** Value of `ADMIN_PASSWORD` in `.env` (default: `SecurWork_Admin_2026!`)

On first run, the backend automatically migrates the database and seeds categories, demo products, CMS pages, and FAQ.

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Set DB to SQLite for quick local dev, or use PostgreSQL
set DB_HOST=localhost
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Client Admin Panels

| Panel | Path | Manages |
|-------|------|---------|
| **React product admin** | `/admin/` | Products, variants, images, stock |
| **Django admin** | `/django-admin/` | Orders, coupons, CMS, FAQ, users |

No developer needed for daily operations. See [docs/HANDOVER.md](docs/HANDOVER.md).

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/products/` | Product catalogue (filters, search, pagination) |
| `GET /api/products/{slug}/` | Product detail |
| `GET /api/categories/` | Category tree |
| `GET /api/cart/` | Current cart |
| `POST /api/cart/` | Add to cart |
| `POST /api/checkout/` | Place order |
| `POST /api/auth/login/` | JWT login |
| `GET /api/pages/{type}/` | CMS pages |
| `POST /api/contact/` | Contact form |

All endpoints accept `?lang=it` or `?lang=en` for bilingual content.

## Languages

- **Italian (IT)** — default
- **English (EN)** — secondary

Frontend: react-i18next (UI strings)  
Backend: django-parler (product/page translations)

## Production Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/DNS-SETUP.md](docs/DNS-SETUP.md).

## License

Proprietary — SecurWork client project.
