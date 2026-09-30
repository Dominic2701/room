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

Vercel supports either the repository root or `source-code` as the project root. Both locations now include a `pyproject.toml`, `requirements.txt`, and `config/wsgi.py` entry point, so Django is discoverable with either setting. If deployment logs report a missing `/var/task/config/wsgi.py`, confirm that the latest commit has deployed and set Vercel's Root Directory to either `.` (repository root) or `source-code`. Vercel collects Django static files from `STATIC_ROOT` for CDN delivery.

Django needs a persistent database; Vercel's function filesystem is temporary, so the local SQLite database is not suitable for deployment. Provision a MySQL database reachable from Vercel, then add these environment variables in **Vercel → Project → Settings → Environment Variables** for the environments you deploy:

- `DJANGO_SECRET_KEY`: a long, random secret value
- `DJANGO_DEBUG`: `False` (debug mode is also forcibly disabled on Vercel)
- `DJANGO_ALLOWED_HOSTS`: any custom domains, comma-separated; Vercel deployment, branch, and project production domains are added automatically from its system environment variables
- `CSRF_TRUSTED_ORIGINS`: any additional HTTPS origins; Vercel domains are added automatically
- `DB_ENGINE`: `mysql`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`: credentials for the persistent MySQL database

Redeploy after adding the variables. Apply database migrations against that database with `python framework\manage.py migrate` from `source-code`, using the same database environment values. Vercel can now complete its build without runtime credentials, but the app will report which required variables are missing on requests until they are configured. Vercel's temporary filesystem also does not persist uploaded `media/` files; use persistent object storage before relying on uploads in production.

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
