from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AdminAccount, Booking, Residency, Room


class BookingFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="guest", password="StrongPass123", email="guest@example.com"
        )
        self.room = Room.objects.create(
            room_number=201,
            room_type=Room.RoomType.DELUXE,
            description="Quiet room",
            price_per_night=Decimal("2500"),
            capacity=2,
            floor=2,
            amenities="WiFi, AC",
        )
        self.start = timezone.localdate() + timedelta(days=10)
        self.end = self.start + timedelta(days=3)

    def test_customer_can_register(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "New",
                "last_name": "Guest",
                "username": "newguest",
                "email": "new@example.com",
                "phone": "1234567890",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("room_list"))
        self.assertTrue(User.objects.filter(username="newguest").exists())

    def test_booking_calculates_total(self):
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.post(
            reverse("book_room", args=[self.room.pk]),
            {
                "check_in": self.start,
                "check_out": self.end,
                "guests": 2,
                "special_request": "Late arrival",
                "payment_method": "GPAY",
            },
        )
        booking = Booking.objects.get()
        self.assertRedirects(response, reverse("payment_checkout", args=[booking.pk]))
        self.assertEqual(booking.number_of_nights, 3)
        self.assertEqual(booking.total_amount, Decimal("7500.00"))
        self.assertEqual(booking.booking_status, Booking.Status.PENDING)
        self.assertEqual(booking.payment.payment_method, "GPAY")
        self.assertEqual(booking.payment.payment_status, "PENDING")
        response = self.client.post(reverse("payment_checkout", args=[booking.pk]))
        self.assertRedirects(response, reverse("booking_detail", args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.payment.payment_status, "SUCCESS")

    def test_overlapping_booking_is_rejected(self):
        Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=self.start,
            check_out=self.end,
            guests=1,
        )
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.post(
            reverse("book_room", args=[self.room.pk]),
            {
                "check_in": self.start + timedelta(days=1),
                "check_out": self.end + timedelta(days=1),
                "guests": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertContains(response, "already booked")

    def test_customer_cannot_access_admin_dashboard(self):
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_private_booking_is_not_visible_to_other_user(self):
        other = User.objects.create_user(username="other", password="StrongPass123")
        booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=self.start,
            check_out=self.end,
            guests=1,
        )
        self.client.login(username="other", password="StrongPass123")
        response = self.client.get(reverse("booking_detail", args=[booking.pk]))
        self.assertEqual(response.status_code, 404)

    def test_booking_quantity_reduces_inventory_and_total(self):
        self.room.total_rooms = 10
        self.room.available_rooms = 10
        self.room.save()
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.post(
            reverse("book_room", args=[self.room.pk]),
            {"check_in": self.start, "check_out": self.end, "guests": 1,
             "number_of_rooms": 3, "payment_method": "GPAY"},
        )
        booking = Booking.objects.get()
        self.assertRedirects(response, reverse("payment_checkout", args=[booking.pk]))
        self.room.refresh_from_db()
        self.assertEqual(self.room.available_rooms, 7)
        self.assertEqual(booking.total_amount, Decimal("22500.00"))

    def test_booking_rejects_quantity_above_inventory(self):
        self.room.total_rooms = 2
        self.room.available_rooms = 2
        self.room.save()
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.post(
            reverse("book_room", args=[self.room.pk]),
            {"check_in": self.start, "check_out": self.end, "guests": 1,
             "number_of_rooms": 3, "payment_method": "GPAY"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 2 rooms are currently available.")
        self.assertFalse(Booking.objects.exists())

    def test_residencies_keep_inventory_independent(self):
        other_residency = Residency.objects.create(
            residency_name="Ocean View Residency",
            provider_name="Ocean View Hospitality",
            location="Puducherry",
        )
        other_room = Room.objects.create(
            residency=other_residency,
            room_number=201,
            room_type=Room.RoomType.DELUXE,
            description="Ocean room",
            price_per_night=Decimal("2800"),
            total_rooms=20,
            available_rooms=20,
            capacity=2,
            floor=2,
            amenities="WiFi",
        )
        self.room.total_rooms = 10
        self.room.available_rooms = 10
        self.room.save()
        self.client.login(username="guest", password="StrongPass123")
        self.client.post(
            reverse("book_room", args=[self.room.pk]),
            {"check_in": self.start, "check_out": self.end, "guests": 1,
             "number_of_rooms": 2, "payment_method": "GPAY"},
        )
        other_room.refresh_from_db()
        self.assertEqual(other_room.available_rooms, 20)

    def test_admin_dashboard_is_scoped_to_admin_residency(self):
        residency = Residency.objects.create(
            residency_name="Admin Residency",
            provider_name="Provider",
            location="Chennai",
        )
        AdminAccount.objects.create(
            residency=residency,
            username="scoped_admin",
            password_hash=make_password("AdminPass123!"),
        )
        session = self.client.session
        session["admin_account_id"] = AdminAccount.objects.get(username="scoped_admin").pk
        session.save()
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Residency")

    def test_cancellation_restores_inventory(self):
        self.room.total_rooms = 5
        self.room.available_rooms = 3
        self.room.save()
        booking = Booking.objects.create(
            user=self.user, room=self.room, check_in=self.start,
            check_out=self.end, guests=1, number_of_rooms=2,
        )
        self.client.login(username="guest", password="StrongPass123")
        response = self.client.post(reverse("cancel_booking", args=[booking.pk]))
        self.assertRedirects(response, reverse("my_bookings"))
        self.room.refresh_from_db()
        self.assertEqual(self.room.available_rooms, 5)

    @override_settings(DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!"))
    def test_admin_registration_verifies_developer_and_hashes_password(self):
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "verify",
                "developer_email": "dominicericson2701@gmail.com",
                "developer_password": "DeveloperPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "create",
                "residency_name": "Grand Palace Residency",
                "provider_name": "Grand Palace Hospitality",
                "location": "Chennai",
                "username": "grandpalace_admin",
                "password": "AdminPass123!",
                "confirm_password": "AdminPass123!",
            },
        )
        self.assertRedirects(response, reverse("admin_login"))
        admin = AdminAccount.objects.get(username="grandpalace_admin")
        self.assertNotEqual(admin.password_hash, "AdminPass123!")
        self.assertTrue(self.client.login(username="unused", password="unused") is False)
        response = self.client.post(
            reverse("admin_login"),
            {"username": "grandpalace_admin", "password": "AdminPass123!"},
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    @override_settings(DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!"))
    def test_wrong_developer_credentials_reject_registration(self):
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "verify",
                "developer_email": "wrong@example.com",
                "developer_password": "DeveloperPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Developer verification failed.")
        self.assertFalse(AdminAccount.objects.exists())

