from django.core.management.base import BaseCommand

from booking.models import Room


class Command(BaseCommand):
    help = "Create or update the starter room inventory."

    rooms = [
        (101, Room.RoomType.SINGLE, 1500, 1, 1, "AC, WiFi, TV, Hot Water"),
        (102, Room.RoomType.DOUBLE, 2000, 2, 1, "AC, WiFi, TV, Hot Water, Breakfast"),
        (
            201,
            Room.RoomType.DELUXE,
            2500,
            2,
            2,
            "AC, WiFi, TV, Hot Water, Room Service",
        ),
        (202, Room.RoomType.DELUXE, 2800, 2, 2, "AC, WiFi, TV, Hot Water, Parking"),
        (
            301,
            Room.RoomType.SUITE,
            5000,
            4,
            3,
            "AC, WiFi, TV, Hot Water, Room Service, Breakfast",
        ),
        (
            302,
            Room.RoomType.FAMILY,
            4000,
            5,
            3,
            "AC, WiFi, TV, Hot Water, Parking, Breakfast",
        ),
    ]

    def handle(self, *args, **options):
        for number, room_type, price, capacity, floor, amenities in self.rooms:
            Room.objects.update_or_create(
                room_number=number,
                defaults={
                    "room_type": room_type,
                    "description": f"A considered {room_type.lower()} room with everything needed for a comfortable stay.",
                    "price_per_night": price,
                    "capacity": capacity,
                    "floor": floor,
                    "amenities": amenities,
                    "status": Room.Status.AVAILABLE,
                },
            )
        self.stdout.write(self.style.SUCCESS("Starter room inventory is ready."))
