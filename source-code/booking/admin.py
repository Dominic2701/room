from django.contrib import admin

from .models import Booking, Payment, Profile, Room


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "price_per_night", "capacity", "status")
    list_filter = ("room_type", "status", "floor")
    search_fields = ("room_id", "room_number", "amenities")
    ordering = ("room_number",)


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
