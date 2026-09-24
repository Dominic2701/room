# Staywise Room Booking

A professional Django + MySQL room booking system for managing rooms, stays, customers, payments, and receipts.

## Features

- Customer registration, login, profile, room search, filters, booking history, cancellation, and PDF receipts
- Server-side date overlap and capacity validation
- Staff dashboard for rooms, bookings, users, payments, and revenue
- Simulated Google Pay, PhonePe, Paytm, Card, and Net Banking payments with no sensitive card or UPI data stored
- Responsive HTML/CSS/JavaScript frontend and Django admin

For a beginner-friendly explanation of the frontend files and Django template syntax, read [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md).

## Technology

Python, Django, Django ORM, MySQL, SQLite for local fallback, ReportLab, Pillow, and python-dotenv.

## Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_rooms
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The custom staff dashboard is at `/admin-dashboard/`; Django admin is at `/django-admin/`.

### MySQL

Create the database once:

```sql
CREATE DATABASE room_booking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Set `DB_ENGINE=mysql`, then update `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env`. Never commit `.env` or real credentials.

## Sample rooms

Create rooms through the staff dashboard or Django admin. Suggested starter inventory: 101 Single (INR 1500), 102 Double (INR 2000), 201 Deluxe (INR 2500), 202 Deluxe (INR 2800), 301 Suite (INR 5000), and 302 Family (INR 4000).

## Tests

```powershell
python manage.py test
python manage.py check
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
