import os

from django.http import HttpResponse


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
                return HttpResponse(
                    "The application is deployed, but its production configuration "
                    f"is incomplete. Configure these Vercel environment variables: "
                    f"{', '.join(missing)}. Then redeploy.",
                    status=503,
                    content_type="text/plain; charset=utf-8",
                )

        return self.get_response(request)
