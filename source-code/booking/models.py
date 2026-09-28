import secrets
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s profile"


class Residency(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    residency_name = models.CharField(max_length=150, unique=True)
    provider_name = models.CharField(max_length=150)
    location = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    main_image = models.ImageField(upload_to="residencies/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "residency"
        ordering = ["residency_name"]

    def __str__(self):
        return self.residency_name


class AdminAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    residencies = models.ManyToManyField(
        Residency, related_name="admins", blank=True
    )
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin"

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def verify_password(self, candidate_password):
        try:
            identify_hasher(self.password_hash)
        except ValueError:
            if not secrets.compare_digest(self.password_hash, candidate_password):
                return False
            self.set_password(candidate_password)
            self.save(update_fields=["password_hash", "updated_at"])
            return True
        return check_password(candidate_password, self.password_hash)

    def __str__(self):
        return self.username


class Room(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        DOUBLE = "DOUBLE", "Double"
        DELUXE = "DELUXE", "Deluxe"
        SUITE = "SUITE", "Suite"
        FAMILY = "FAMILY", "Family"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    room_id = models.CharField(max_length=12, unique=True, editable=False, default="")
    residency = models.ForeignKey(
        Residency, on_delete=models.PROTECT, related_name="rooms"
    )
    room_number = models.PositiveIntegerField()
    room_type = models.CharField(max_length=10, choices=RoomType.choices)
    description = models.TextField()
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    total_rooms = models.PositiveIntegerField(default=1)
    available_rooms = models.PositiveIntegerField(default=1)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    floor = models.PositiveIntegerField()
    amenities = models.CharField(max_length=255, help_text="Comma-separated amenities")
    image = models.ImageField(upload_to="rooms/", blank=True, null=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.AVAILABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "room_details"
        ordering = ["room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["residency", "room_number"],
                name="room_number_unique_per_residency",
            ),
            models.CheckConstraint(
                condition=models.Q(available_rooms__lte=models.F("total_rooms")),
                name="room_available_not_above_total",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.room_id:
            self.room_id = f"RM-{uuid4().hex[:8].upper()}"
        if not self.residency_id:
            self.residency, _ = Residency.objects.get_or_create(
                residency_name="Legacy Residency",
                defaults={
                    "provider_name": "Staywise",
                    "location": "Unassigned",
                },
            )
        super().save(*args, **kwargs)

    @property
    def amenity_list(self):
        return [item.strip() for item in self.amenities.split(",") if item.strip()]

    def __str__(self):
        return f"Room {self.room_number} - {self.get_room_type_display()}"


class GalleryImage(models.Model):
    class ImageType(models.TextChoices):
        ROOM = "ROOM", "Room"
        BEDROOM = "BEDROOM", "Bedroom"
        BATHROOM = "BATHROOM", "Bathroom"
        PARKING = "PARKING", "Parking"
        RECEPTION = "RECEPTION", "Reception"
        DINING = "DINING", "Dining area"
        LOBBY = "LOBBY", "Lobby"
        EXTERIOR = "EXTERIOR", "Exterior"
        AMENITIES = "AMENITIES", "Amenities"
        OTHER = "OTHER", "Other"

    residency = models.ForeignKey(
        Residency,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        blank=True,
        null=True,
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        blank=True,
        null=True,
    )
    image = models.ImageField(upload_to="gallery/")
    image_type = models.CharField(
        max_length=12, choices=ImageType.choices, default=ImageType.OTHER
    )
    caption = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(residency__isnull=False, room__isnull=True)
                    | models.Q(residency__isnull=True, room__isnull=False)
                ),
                name="gallery_image_has_one_parent",
            )
        ]


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    booking_id = models.CharField(
        max_length=14, unique=True, editable=False, default=""
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    residency = models.ForeignKey(
        Residency, on_delete=models.PROTECT, related_name="bookings"
    )
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField()
    number_of_rooms = models.PositiveIntegerField(default=1)
    number_of_nights = models.PositiveIntegerField(default=0)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    booking_status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    booking_date = models.DateTimeField(auto_now_add=True)
    special_request = models.TextField(blank=True)

    class Meta:
        db_table = "booking_details"
        ordering = ["-booking_date"]

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = f"BK-{uuid4().hex[:8].upper()}"
        self.number_of_nights = (self.check_out - self.check_in).days
        if not self.price_per_night:
            self.price_per_night = self.room.price_per_night
        if not self.residency_id:
            self.residency = self.room.residency
        self.total_amount = (
            self.price_per_night * self.number_of_rooms * self.number_of_nights
        )
        super().save(*args, **kwargs)

    @property
    def is_cancellable(self):
        return (
            self.booking_status in {self.Status.PENDING, self.Status.CONFIRMED}
            and self.check_in >= timezone.localdate()
        )

    def __str__(self):
        return self.booking_id


class Payment(models.Model):
    class Method(models.TextChoices):
        GPAY = "GPAY", "Google Pay"
        PHONEPE = "PHONEPE", "PhonePe"
        PAYTM = "PAYTM", "Paytm"
        CARD = "CARD", "Card"
        NET_BANKING = "NET_BANKING", "Net banking"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    payment_id = models.CharField(
        max_length=14, unique=True, editable=False, default=""
    )
    booking = models.OneToOneField(
        Booking, on_delete=models.PROTECT, related_name="payment"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=15, choices=Method.choices, default=Method.GPAY
    )
    payment_status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    transaction_id = models.CharField(max_length=80, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.payment_id
