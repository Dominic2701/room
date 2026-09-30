import logging
import ipaddress
import os
from urllib.parse import urlparse

from django.db.utils import OperationalError
from django.http import HttpResponse


logger = logging.getLogger(__name__)


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
                    for name in (
                        "DB_NAME",
                        "DB_USER",
                        "DB_PASSWORD",
                        "DB_HOST",
                        "DB_PORT",
                    )
                    if not os.getenv(name)
                )
                db_host = os.getenv("DB_HOST", "").strip()
                if db_host and _is_local_database_host(db_host):
                    missing.append(
                        "DB_HOST must be the external database hostname, "
                        "not a loopback address"
                    )
                db_port = os.getenv("DB_PORT", "").strip()
                if db_port and (
                    not db_port.isdecimal()
                    or len(db_port) > 5
                    or not 1 <= int(db_port) <= 65535
                ):
                    missing.append(
                        "DB_PORT must be the valid port from the database "
                        "provider's connection details"
                    )

            if missing:
                return HttpResponse(
                    "The application is deployed, but its production configuration "
                    f"is incomplete. Configure these Vercel environment variables: "
                    f"{', '.join(missing)}. Then redeploy.",
                    status=503,
                    content_type="text/plain; charset=utf-8",
                )

        try:
            return self.get_response(request)
        except OperationalError:
            if not os.getenv("VERCEL"):
                raise
            logger.exception("Database connection failed while handling request")
            return HttpResponse(
                "The application could not reach its database. Verify DB_HOST "
                "and DB_PORT against the provider's connection details, ensure "
                "the database is running, and allow connections from the Vercel "
                "deployment.",
                status=503,
                content_type="text/plain; charset=utf-8",
            )
