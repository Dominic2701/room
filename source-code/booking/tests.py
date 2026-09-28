from datetime import timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from dotenv import dotenv_values
from PIL import Image

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

    def make_image(self, name="test.png"):
        buffer = BytesIO()
        Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            name, buffer.getvalue(), content_type="image/png"
        )

    def login_admin(self, residency=None):
        residency = residency or self.room.residency
        admin = AdminAccount.objects.create(
            username=f"admin_{AdminAccount.objects.count()}",
            password_hash=make_password("AdminPass123!"),
        )
        admin.residencies.add(residency)
        session = self.client.session
        session["admin_account_id"] = admin.pk
        session.save()
        return admin

    def assign_active_admin(self, residency):
        admin = AdminAccount.objects.create(
            username=f"room_manager_{AdminAccount.objects.count()}",
            password_hash=make_password("AdminPass123!"),
        )
        admin.residencies.add(residency)
        return admin

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
        self.assign_active_admin(self.room.residency)
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
        self.assign_active_admin(self.room.residency)
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
        self.assign_active_admin(self.room.residency)
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
        self.assign_active_admin(self.room.residency)
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
        self.assign_active_admin(self.room.residency)
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

    def test_only_rooms_in_active_admin_managed_residencies_are_public(self):
        self.client.force_login(self.user)

        self.assertNotContains(self.client.get(reverse("home")), "Legacy Residency")
        self.assertNotContains(
            self.client.get(reverse("room_list")), "Legacy Residency"
        )
        self.assertEqual(
            self.client.get(
                reverse("room_detail", args=[self.room.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("book_room", args=[self.room.pk])
            ).status_code,
            404,
        )

        admin = self.assign_active_admin(self.room.residency)
        home_response = self.client.get(reverse("home"))
        list_response = self.client.get(reverse("room_list"))
        detail_response = self.client.get(
            reverse("room_detail", args=[self.room.pk])
        )
        booking_response = self.client.get(
            reverse("book_room", args=[self.room.pk])
        )

        self.assertContains(home_response, "Legacy Residency")
        self.assertContains(list_response, "Legacy Residency")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(booking_response.status_code, 200)
        self.assertEqual(admin.status, AdminAccount.Status.ACTIVE)

    def test_admin_dashboard_is_scoped_to_admin_residency(self):
        residency = Residency.objects.create(
            residency_name="Admin Residency",
            provider_name="Provider",
            location="Chennai",
        )
        admin = AdminAccount.objects.create(
            username="scoped_admin",
            password_hash="AdminPass123!",
        )
        admin.residencies.add(residency)
        session = self.client.session
        session["admin_account_id"] = admin.pk
        session.save()
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Residency")
        self.assertNotContains(response, "Legacy Residency")

    def test_admin_can_manage_multiple_residencies_and_create_rooms(self):
        admin = self.login_admin()
        response = self.client.post(
            reverse("admin_residency_add"),
            {
                "residency_name": "Ocean View",
                "provider_name": "Ocean Group",
                "location": "Puducherry",
                "status": Residency.Status.ACTIVE,
                "main_image": self.make_image("ocean.png"),
                "gallery_images": [self.make_image("lobby.png")],
            },
        )
        self.assertRedirects(response, reverse("admin_residencies"))
        residency = Residency.objects.get(residency_name="Ocean View")
        self.assertTrue(admin.residencies.filter(pk=residency.pk).exists())
        self.assertTrue(residency.main_image.name.startswith("residencies/"))
        self.assertEqual(residency.gallery_images.count(), 1)

        response = self.client.post(
            reverse("admin_room_add"),
            {
                "residency": residency.pk,
                "room_number": 101,
                "room_type": Room.RoomType.DELUXE,
                "description": "Bright room",
                "price_per_night": "2500.00",
                "total_rooms": 6,
                "available_rooms": 6,
                "capacity": 3,
                "floor": 1,
                "amenities": "WiFi, AC",
                "status": Room.Status.AVAILABLE,
                "image": self.make_image("room.png"),
                "gallery_images": [self.make_image("bathroom.png")],
            },
        )
        self.assertRedirects(response, reverse("admin_rooms"))
        room = Room.objects.get(residency=residency)
        self.assertTrue(room.image.name.startswith("rooms/"))
        self.assertEqual(room.gallery_images.count(), 1)
        self.assertContains(self.client.get(reverse("room_list")), "Ocean View")
        detail = self.client.get(reverse("room_detail", args=[room.pk]))
        self.assertContains(detail, room.image.url)
        self.assertContains(detail, residency.main_image.url)

    def test_admin_cannot_manage_an_unassigned_residency(self):
        self.login_admin()
        other = Residency.objects.create(
            residency_name="Private Residency",
            provider_name="Private Provider",
            location="Chennai",
        )
        self.assertEqual(
            self.client.get(
                reverse("admin_residency_edit", args=[other.pk])
            ).status_code,
            404,
        )

    def test_admin_cannot_set_availability_above_unreserved_inventory(self):
        self.room.total_rooms = 5
        self.room.available_rooms = 3
        self.room.save()
        Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=self.start,
            check_out=self.end,
            guests=1,
            number_of_rooms=2,
        )
        admin = self.login_admin(self.room.residency)
        form = __import__("booking.forms", fromlist=["RoomForm"]).RoomForm(
            {
                "residency": self.room.residency.pk,
                "room_number": self.room.room_number,
                "room_type": self.room.room_type,
                "description": self.room.description,
                "price_per_night": self.room.price_per_night,
                "total_rooms": 5,
                "available_rooms": 4,
                "capacity": self.room.capacity,
                "floor": self.room.floor,
                "amenities": self.room.amenities,
                "status": self.room.status,
            },
            instance=self.room,
            admin_account=admin,
        )
        self.assertFalse(form.is_valid())

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

    @override_settings(
        DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!"),
    )
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
        self.assertTrue(check_password("AdminPass123!", admin.password_hash))
        self.assertTrue(self.client.login(username="unused", password="unused") is False)
        response = self.client.post(
            reverse("admin_login"),
            {"username": "grandpalace_admin", "password": "AdminPass123!"},
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_admin_login_upgrades_legacy_plaintext_password(self):
        admin = AdminAccount.objects.create(
            username="legacy_admin",
            password_hash="AdminPass123!",
        )
        admin.residencies.add(self.room.residency)

        response = self.client.post(
            reverse("admin_login"),
            {"username": "legacy_admin", "password": "AdminPass123!"},
        )

        self.assertRedirects(response, reverse("admin_dashboard"))
        admin.refresh_from_db()
        self.assertNotEqual(admin.password_hash, "AdminPass123!")
        self.assertTrue(check_password("AdminPass123!", admin.password_hash))

    @override_settings(
        DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!")
    )
    def test_admin_registration_verifies_hashed_developer_password(self):
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "verify",
                "developer_email": "dominicericson2701@gmail.com",
                "developer_password": "DeveloperPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Developer verification successful.")

    def test_set_developer_password_retries_mismatch_and_saves_verified_hash(self):
        with TemporaryDirectory() as temporary_directory:
            env_path = Path(temporary_directory) / ".env"
            env_path.write_text(
                'DEVELOPER_PASSWORD_HASH="existing-hash"\n',
                encoding="utf-8",
            )
            output = StringIO()
            errors = StringIO()

            with (
                patch(
                    "booking.management.commands.set_developer_password.getpass",
                    side_effect=[
                        "FirstAttempt123!",
                        "NotTheSame123!",
                        "NewDeveloperPass123!",
                        "NewDeveloperPass123!",
                    ],
                ),
                override_settings(BASE_DIR=Path(temporary_directory)),
            ):
                call_command(
                    "set_developer_password",
                    stdout=output,
                    stderr=errors,
                )

            saved_hash = dotenv_values(env_path).get("DEVELOPER_PASSWORD_HASH", "")
            self.assertTrue(
                check_password("NewDeveloperPass123!", saved_hash)
            )
            self.assertFalse(check_password("FirstAttempt123!", saved_hash))
            self.assertIn("saved and verified", output.getvalue())
            self.assertIn("Passwords do not match", errors.getvalue())
            self.assertNotIn(
                "FirstAttempt123!",
                env_path.read_text(encoding="utf-8"),
            )

    @override_settings(
        DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!"),
    )
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
        self.assertContains(response, "Invalid developer credentials.")
        self.assertFalse(AdminAccount.objects.exists())

    @override_settings(
        DEVELOPER_PASSWORD_HASH=make_password("DeveloperPass123!"),
    )
    def test_wrong_developer_password_rejects_registration(self):
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "verify",
                "developer_email": "dominicericson2701@gmail.com",
                "developer_password": "WrongPassword123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid developer credentials.")
        self.assertFalse(AdminAccount.objects.exists())

    @override_settings(DEVELOPER_PASSWORD_HASH="")
    def test_admin_registration_reports_missing_developer_password(self):
        response = self.client.post(
            reverse("admin_register"),
            {
                "action": "verify",
                "developer_email": "dominicericson2701@gmail.com",
                "developer_password": "any-password",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Developer verification is not configured.")
        self.assertFalse(AdminAccount.objects.exists())
