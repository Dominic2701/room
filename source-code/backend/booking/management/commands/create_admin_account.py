from getpass import getpass

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from booking.models import AdminAccount, Residency


class Command(BaseCommand):
    help = "Create a residency-scoped admin account from the local terminal."

    def handle(self, *args, **options):
        residency_name = input("Residency name: ").strip()
        provider_name = input("Provider name: ").strip()
        location = input("Location: ").strip()
        username = input("Admin username: ").strip()
        password = getpass("Admin password: ")
        confirmation = getpass("Confirm admin password: ")

        if not all((residency_name, provider_name, location, username, password)):
            raise CommandError("All fields are required.")
        if password != confirmation:
            raise CommandError("The passwords do not match.")
        if AdminAccount.objects.filter(username=username).exists():
            raise CommandError("That admin username already exists.")

        residency, _ = Residency.objects.get_or_create(
            residency_name=residency_name,
            defaults={"provider_name": provider_name, "location": location},
        )
        admin = AdminAccount.objects.create(
            username=username,
            password_hash=make_password(password),
        )
        admin.residencies.add(residency)
        self.stdout.write(
            self.style.SUCCESS(
                "Admin account created. Sign in at /admin-login/."
            )
        )
