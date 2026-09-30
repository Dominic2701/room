from unittest.mock import patch

from django.db.utils import OperationalError
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
            "DB_PORT": "3306",
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
            "DB_PORT": "25123",
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
            "DATABASE_URL": "postgres://user:password@db.example.com/booking",
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
            "DATABASE_URL": "mysql://user:password@localhost:3306/booking",
        }
        middleware = VercelConfigurationMiddleware(
            lambda request: HttpResponse("ok")
        )

        with patch.dict("os.environ", environment, clear=True):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"DATABASE_URL must point", response.content)

    def test_requires_explicit_database_port_on_vercel(self):
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

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"DB_PORT", response.content)

    def test_reports_unreachable_database_on_vercel(self):
        environment = {
            "VERCEL": "1",
            "DJANGO_SECRET_KEY": "test-secret",
            "DB_ENGINE": "mysql",
            "DB_NAME": "booking",
            "DB_USER": "booking",
            "DB_PASSWORD": "test-password",
            "DB_HOST": "mysql.example.com",
            "DB_PORT": "25123",
        }

        def raise_connection_error(request):
            raise OperationalError("connection timed out")

        middleware = VercelConfigurationMiddleware(raise_connection_error)

        with (
            patch.dict("os.environ", environment, clear=True),
            self.assertLogs("booking.middleware", level="ERROR"),
        ):
            response = middleware(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"could not reach its database", response.content)
        self.assertIn(
            b"allow connections from the Vercel deployment", response.content
        )
