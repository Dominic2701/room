from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from .middleware import VercelConfigurationMiddleware


class VercelConfigurationMiddlewareTests(SimpleTestCase):
    def test_rejects_loopback_database_host_on_vercel(self):
        environment = {
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "test-secret",
            "DB_ENGINE": "mysql",
            "DB_NAME": "booking",
            "DB_USER": "booking",
            "DB_PASSWORD": "test-password",
            "DB_HOST": "127.0.0.1",
        }
        called = False

        def get_response(request):
            nonlocal called
            called = True
            return None

        middleware = VercelConfigurationMiddleware(get_response)
        with patch.dict("os.environ", environment, clear=True):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 503)
        self.assertIn(
            b"DB_HOST must be the external database hostname", response.content
        )
        self.assertFalse(called)

    def test_allows_external_database_host_on_vercel(self):
        environment = {
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "test-secret",
            "DB_ENGINE": "mysql",
            "DB_NAME": "booking",
            "DB_USER": "booking",
            "DB_PASSWORD": "test-password",
            "DB_HOST": "mysql.example.com",
        }
        middleware = VercelConfigurationMiddleware(
            lambda request: HttpResponse("ok")
        )

        with patch.dict("os.environ", environment, clear=True):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 200)

    def test_allows_database_url_on_vercel(self):
        environment = {
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "test-secret",
            "DATABASE_URL": "postgres://u:p@ep-cool-name.neon.tech/booking",
        }
        middleware = VercelConfigurationMiddleware(
            lambda request: HttpResponse("ok")
        )

        with patch.dict("os.environ", environment, clear=True):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 200)

    def test_rejects_loopback_database_url_on_vercel(self):
        environment = {
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "test-secret",
            "DATABASE_URL": "mysql://root:pw@localhost:3306/booking",
        }
        middleware = VercelConfigurationMiddleware(
            lambda request: HttpResponse("ok")
        )

        with patch.dict("os.environ", environment, clear=True):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"DATABASE_URL must point", response.content)
