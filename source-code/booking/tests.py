from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Booking, Room


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
