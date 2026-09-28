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
