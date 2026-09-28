from django.contrib import admin

from .models import (
    AdminAccount,
    Booking,
    GalleryImage,
    Payment,
    Profile,
    Residency,
    Room,
)


@admin.register(Residency)
class ResidencyAdmin(admin.ModelAdmin):
    list_display = (
        "residency_name",
        "provider_name",
        "location",
        "phone",
        "email",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("residency_name", "provider_name", "location")


@admin.register(AdminAccount)
class AdminAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "residency_list", "status", "created_at")
    list_filter = ("status", "residencies")
    search_fields = ("username", "residencies__residency_name")
    exclude = ("password_hash",)

    @admin.display(description="Residencies")
    def residency_list(self, obj):
        return ", ".join(obj.residencies.values_list("residency_name", flat=True))


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "price_per_night", "total_rooms", "available_rooms", "status")
    list_filter = ("room_type", "status", "floor")
    search_fields = ("room_id", "room_number", "amenities")
    ordering = ("room_number",)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("image_type", "caption", "residency", "room", "created_at")
    list_filter = ("image_type",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_id",
        "user",
        "room",
        "check_in",
        "check_out",
        "total_amount",
        "booking_status",
    )
    list_filter = ("booking_status", "booking_date")
    search_fields = ("booking_id", "user__username", "room__room_number")
    readonly_fields = (
        "booking_id",
        "number_of_nights",
        "price_per_night",
        "total_amount",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "booking",
        "amount",
        "payment_method",
        "payment_status",
        "payment_date",
    )
    list_filter = ("payment_method", "payment_status")
    search_fields = ("payment_id", "transaction_id", "booking__booking_id")
