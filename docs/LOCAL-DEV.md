# SecurWork — Local Development

## Option A: Docker (recommended)

```powershell
cd "c:\Users\wwwso\Desktop\my projects\securwork"
docker compose up -d --build
```

- Storefront: http://localhost:5180
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/ (admin / see `.env` ADMIN_PASSWORD)

```powershell
# View logs
docker compose logs -f backend

# Run Django commands
docker compose exec backend python manage.py seed_data
docker compose exec backend python manage.py createsuperuser

# Stop
docker compose down

# Fresh database
docker compose down -v
docker compose up -d --build
```

## Option B: Manual setup (Windows quick start)

**Use two terminals** — `runserver` blocks the shell, so you cannot start both in one command.

```powershell
# Terminal 1 — backend
cd "c:\Users\wwwso\Desktop\my projects\securwork\backend"
.\venv\Scripts\Activate.ps1
$env:USE_SQLITE="true"
$env:SECRET_KEY="dev"
python manage.py runserver

# Terminal 2 — frontend
cd "c:\Users\wwwso\Desktop\my projects\securwork\frontend"
npm run dev
```

**Or use the helper script** (opens two windows automatically):

```powershell
cd "c:\Users\wwwso\Desktop\my projects\securwork"
.\scripts\dev.ps1
```

Open the storefront at **http://localhost:5180** (not port 8000 or 5173).

SecurWork uses port **5180** on purpose — port 5173 is Vite's default and is often already used by another project on your machine.

Port 8000 is API/admin only. In dev mode, visiting http://localhost:8000 redirects to the frontend.

---

## Option B2: Manual setup (detailed)

### PostgreSQL

Install PostgreSQL locally and create database:

```sql
CREATE DATABASE securwork;
CREATE USER securwork WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE securwork TO securwork;
```

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copy .env from project root or set variables
$env:DB_HOST="localhost"
$env:DB_PASSWORD="yourpassword"
$env:SECRET_KEY="dev-secret"

python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api`, `/media`, and `/admin` to `http://localhost:8000`.

## Useful commands

```bash
# Create migrations after model changes
python manage.py makemigrations
python manage.py migrate

# Django shell
python manage.py shell

# Build frontend for production
cd frontend && npm run build
```
