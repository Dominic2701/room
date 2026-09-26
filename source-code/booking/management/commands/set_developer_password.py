from getpass import getpass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Hash the developer verification password into the local .env file."

    def handle(self, *args, **options):
        password = getpass("Developer password: ")
        if not password:
            raise CommandError("A developer password is required.")

        env_path = Path(settings.BASE_DIR) / ".env"
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        setting = f"DEVELOPER_PASSWORD_HASH={make_password(password)}"
        replaced = False
        updated_lines = []
        for line in lines:
            if line.startswith("DEVELOPER_PASSWORD_HASH="):
                updated_lines.append(setting)
                replaced = True
            else:
                updated_lines.append(line)
        if not replaced:
            updated_lines.extend(["", setting])
        env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Developer password hash saved to source-code/.env."))
