from getpass import getpass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.management.base import BaseCommand
from dotenv import dotenv_values


class Command(BaseCommand):
    help = "Save the developer verification password into the local .env file."

    def handle(self, *args, **options):
        while True:
            password = getpass("Developer password: ")
            if not password:
                self.stderr.write(
                    self.style.ERROR("A developer password is required.")
                )
                continue

            confirmation = getpass("Confirm developer password: ")
            if password != confirmation:
                self.stderr.write(
                    self.style.ERROR(
                        "Passwords do not match. Nothing was changed; try again."
                    )
                )
                continue

            if "\n" in password or "\r" in password:
                self.stderr.write(
                    self.style.ERROR(
                        "The password cannot contain a newline. Nothing was changed."
                    )
                )
                continue
            break

        env_path = Path(settings.BASE_DIR) / ".env"
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        password_hash = make_password(password)
        setting = f'DEVELOPER_PASSWORD_HASH="{password_hash}"'
        replaced = False
        updated_lines = []
        for line in lines:
            if line.startswith("DEVELOPER_PASSWORD=") or line.startswith(
                "DEVELOPER_PASSWORD_HASH="
            ):
                updated_lines.append(setting)
                replaced = True
            else:
                updated_lines.append(line)
        if not replaced:
            updated_lines.extend(["", setting])
        env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        saved_hash = dotenv_values(env_path).get("DEVELOPER_PASSWORD_HASH", "")
        if not saved_hash or not check_password(password, saved_hash):
            raise CommandError(
                "The developer password hash could not be verified after saving."
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Developer password saved and verified. Restart the server to load it."
            )
        )
