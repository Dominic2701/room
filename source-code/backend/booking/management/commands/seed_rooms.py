from django.core.management.base import BaseCommand

from booking.models import Residency, Room


class Command(BaseCommand):
    help = "Create or update the starter room inventory."

    rooms = [
        ("Grand Palace Residency", "Grand Palace Hospitality", "Chennai", 101, Room.RoomType.SINGLE, 1500, 1, 1, 10, "AC, WiFi, TV, Hot Water"),
        ("Grand Palace Residency", "Grand Palace Hospitality", "Chennai", 102, Room.RoomType.DOUBLE, 2000, 2, 1, 8, "AC, WiFi, TV, Hot Water, Breakfast"),
        (
            "Grand Palace Residency", "Grand Palace Hospitality", "Chennai",
            201,
            Room.RoomType.DELUXE,
            2500,
            2,
            2,
            6, "AC, WiFi, TV, Hot Water, Room Service",
        ),
        ("Ocean View Residency", "Ocean View Hospitality", "Puducherry", 301, Room.RoomType.DELUXE, 2800, 2, 2, 20, "AC, WiFi, TV, Hot Water, Parking"),
        (
            "Ocean View Residency", "Ocean View Hospitality", "Puducherry",
            302,
            Room.RoomType.SUITE,
            5000,
            4,
            3,
            18, "AC, WiFi, TV, Hot Water, Room Service, Breakfast",
        ),
        (
            "Green Park Residency", "Green Park Hospitality", "Bengaluru",
            401,
            Room.RoomType.FAMILY,
            4000,
            5,
            3,
            12, "AC, WiFi, TV, Hot Water, Parking, Breakfast",
        ),
    ]

    def handle(self, *args, **options):
        for residency_name, provider_name, location, number, room_type, price, capacity, floor, total_rooms, amenities in self.rooms:
            residency, _ = Residency.objects.get_or_create(
                residency_name=residency_name,
                defaults={"provider_name": provider_name, "location": location},
            )
            Room.objects.update_or_create(
                residency=residency,
                room_number=number,
                defaults={
                    "residency": residency,
                    "room_type": room_type,
                    "description": f"A considered {room_type.lower()} room with everything needed for a comfortable stay.",
                    "price_per_night": price,
                    "total_rooms": total_rooms,
                    "available_rooms": total_rooms,
                    "capacity": capacity,
                    "floor": floor,
                    "amenities": amenities,
                    "status": Room.Status.AVAILABLE,
                },
            )
        self.stdout.write(self.style.SUCCESS("Starter room inventory is ready."))
