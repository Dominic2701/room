# Staywise Room Booking

A professional Django + MySQL room booking system for managing rooms, stays, customers, payments, and receipts.

## Features

- Customer registration, login, profile, room search, filters, booking history, cancellation, and PDF receipts
- Server-side date overlap and capacity validation
- Staff dashboard for rooms, bookings, users, payments, and revenue
- Simulated Google Pay, PhonePe, Paytm, Card, and Net Banking payments with no sensitive card or UPI data stored
- Responsive HTML/CSS/JavaScript frontend and Django admin

For a beginner-friendly explanation of the frontend files and Django template syntax, read [FRONTEND_GUIDE.md](frontend/FRONTEND_GUIDE.md).

## Technology

Python, Django, Django ORM, MySQL, SQLite for local fallback, ReportLab, Pillow, and python-dotenv.

## Setup

```powershell
Set-Location "C:\gen ai\room_booking"
.\.venv\Scripts\Activate.ps1
Set-Location .\source-code
python -m pip install -r framework\requirements.txt
python framework\manage.py migrate
python framework\manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/`. The custom staff dashboard is at `/admin-dashboard/`; Django admin is at `/django-admin/`.

### MySQL

Create the database once:

```sql
CREATE DATABASE room_booking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Set `DB_ENGINE=mysql`, then update `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env`. Never commit `.env` or real credentials.

For admin registration, set `DEVELOPER_EMAIL` in the ignored local `.env`, then run `python framework\manage.py set_developer_password` from `source-code` to configure the developer password. The command stores a Django password hash in `DEVELOPER_PASSWORD_HASH`; verification runs server-side. Admin and customer passwords are also securely hashed and are never stored in plain text.

Each admin account can manage one or more residencies. Use **Residencies** in the staff dashboard to add/edit properties, upload a main image, and manage categorized gallery photos. Room forms support a main image and multiple gallery images. Uploaded files are stored under `media/`; `MEDIA_URL` is served during development.

## Sample rooms

Create rooms through the staff dashboard or Django admin. Suggested starter inventory: 101 Single (INR 1500), 102 Double (INR 2000), 201 Deluxe (INR 2500), 202 Deluxe (INR 2800), 301 Suite (INR 5000), and 302 Family (INR 4000).

## Deploy to Vercel

1. **Import the repo** in Vercel and leave **Root Directory** as the repository root (`.`). Vercel detects Django from `manage.py`; the entrypoint is `config.wsgi:application` (set in `pyproject.toml`). Framework preset: Django (or "Other"). Leave Build/Output commands empty.
2. **Create a hosted database.** Vercel's filesystem is temporary, so SQLite and `localhost` MySQL cannot work there. Easiest: Vercel → **Storage** (Marketplace) → **Neon Postgres** → connect it to this project. That sets `DATABASE_URL` automatically. Hosted MySQL (TiDB Cloud, Aiven) also works: set `DATABASE_URL=mysql://user:password@host:port/dbname` and `DB_SSL=True`.
3. **Add environment variables** (Project → Settings → Environment Variables):
   - `DJANGO_SECRET_KEY`: a long random value
   - `DATABASE_URL`: set by the Neon integration, or your own connection string
   - Optional: `DJANGO_ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` for a custom domain (Vercel domains are added automatically)
   - Optional email settings: `EMAIL_USER`, `EMAIL_PASSWORD`, `DEVELOPER_EMAIL`, `DEVELOPER_PASSWORD_HASH`
4. **Redeploy.** The build runs `build.py`, which applies migrations to the hosted database, and Vercel collects static files to its CDN automatically.
5. **Create the first admin** from your computer against the same database: put the same `DATABASE_URL` in a local `.env` next to `framework/`, then run `python framework\manage.py create_admin_account` (or `createsuperuser`).

The older `DB_ENGINE=mysql` + `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` variables still work instead of `DATABASE_URL`; `DB_HOST` must be the provider's hostname, never `127.0.0.1` or `localhost`. Until a database is configured the site shows a 503 message listing what is missing.

**Uploaded images:** files saved to `media/` do not persist on Vercel and are not served when `DEBUG` is off. Use object storage (for example Vercel Blob, Cloudinary or S3 via `django-storages`) before relying on image uploads in production.

## Tests

```powershell
Set-Location "C:\gen ai\room_booking\source-code"
python framework\manage.py test
python framework\manage.py check
```

## GitHub

```powershell
git init
git add .
git commit -m "Initial room booking application"
git remote add origin https://github.com/YOUR_USERNAME/room-booking.git
git push -u origin main
```

Do not push `.env`, passwords, secret keys, or production media.
