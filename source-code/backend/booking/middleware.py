import os

from django.core.exceptions import ImproperlyConfigured


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
            if os.getenv("DB_ENGINE", "").lower() != "mysql":
                missing.append("DB_ENGINE=mysql (persistent database required)")
            else:
                missing.extend(
                    name
                    for name in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST")
                    if not os.getenv(name)
                )

            if missing:
                raise ImproperlyConfigured(
                    "Configure these Vercel environment variables before using "
                    f"the app: {', '.join(missing)}."
                )

        return self.get_response(request)
