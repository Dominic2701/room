import ipaddress
import os
from urllib.parse import urlparse

from django.http import HttpResponse


def _is_local_database_host(host):
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class VercelConfigurationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if os.getenv("VERCEL"):
            missing = [
                name
                for name in ("DJANGO_SECRET_KEY",)
                if not os.getenv(name)
            ]
            database_url = (
                os.getenv("DATABASE_URL")
                or os.getenv("POSTGRES_URL")
                or os.getenv("MYSQL_URL")
                or ""
            ).strip()
            if database_url:
                db_host = urlparse(database_url).hostname or ""
                if not db_host or _is_local_database_host(db_host):
                    missing.append(
                        "DATABASE_URL must point to an external database host, "
                        "not a loopback address"
                    )
            elif os.getenv("DB_ENGINE", "").lower() != "mysql":
                missing.append(
                    "DATABASE_URL (or DB_ENGINE=mysql with DB_* settings) "
                    "for a persistent database"
                )
            else:
                missing.extend(
                    name
                    for name in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
                    if not os.getenv(name)
                )
                db_host = os.getenv("DB_HOST", "").strip()
                if db_host and _is_local_database_host(db_host):
                    missing.append(
                        "DB_HOST must be the external database hostname, "
                        "not a loopback address"
                    )

            if missing:
                return HttpResponse(
                    "The application is deployed, but its production configuration "
                    f"is incomplete. Configure these Vercel environment variables: "
                    f"{', '.join(missing)}. Then redeploy.",
                    status=503,
                    content_type="text/plain; charset=utf-8",
                )

        return self.get_response(request)
