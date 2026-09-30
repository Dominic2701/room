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

## Deploy to Vercel (free)

Everything below uses free plans with hard limits, so nothing is charged. When a free limit is reached the service stops or pauses until the next month instead of billing you.

| Piece | Free service | Free allowance |
| --- | --- | --- |
| Website hosting | Vercel Hobby | Personal, non-commercial use only |
| Database | Neon Postgres (via Vercel Storage) | 0.5 GB per project |
| Uploaded images | Vercel Blob | 1 GB storage, 2,000 uploads/month, 10 GB downloads/month |

1. **Import the repo** in Vercel (Hobby plan). Leave **Root Directory** as the repository root (`.`) and leave the Build/Output commands empty. Vercel detects Django from `manage.py`; the entrypoint `config.wsgi:application` is set in `pyproject.toml`.
2. **Add the database:** Project → **Storage** → **Create Database** → **Neon** (free plan) → connect it to the project. This sets `DATABASE_URL`.
3. **Add image storage:** Project → **Storage** → **Create** → **Blob** → connect it to the project. This sets `BLOB_READ_WRITE_TOKEN`, and uploads go to Blob automatically.
4. **Add one variable** under Settings → Environment Variables: `DJANGO_SECRET_KEY` = a long random value. Optional: `DJANGO_ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` for a custom domain; `EMAIL_USER`, `EMAIL_PASSWORD`, `DEVELOPER_EMAIL`, `DEVELOPER_PASSWORD_HASH` for email and admin registration.
5. **Redeploy.** The build runs `build.py`, which applies migrations to the database; Vercel collects static files to its CDN.
6. **Create the first admin** from your computer: put the same `DATABASE_URL` in `source-code/.env`, then run `python framework\manage.py create_admin_account` (or `createsuperuser`) from `source-code`.

Notes:
- Preview deployments use the same database unless you give them a separate one, and their migrations run against it.
- Images uploaded before Blob was connected (in your local `media/` folder) are not copied; re-upload them through the dashboard.
- Hosted MySQL also works instead of Neon: set `DATABASE_URL=mysql://user:password@host:port/dbname` and `DB_SSL=True`. The older `DB_ENGINE=mysql` + `DB_*` variables still work; `DB_HOST` must never be `127.0.0.1` or `localhost`.
- Until a database is configured, the site shows a 503 message listing what is missing.
- Locally nothing changes: without these variables the app uses SQLite (or your local MySQL) and the `media/` folder.

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
