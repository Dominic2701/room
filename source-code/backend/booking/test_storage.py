import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from vercel.blob import BlobNotFoundError

from .models import Residency
from .storage import VercelBlobStorage

TOKEN = "vercel_blob_rw_AbC123Store_secretpart"


def _png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeBlobService:
    """Stands in for the Vercel Blob API so tests run offline."""

    def __init__(self):
        self.files = {}

    def _path(self, url):
        return url.split(".blob.vercel-storage.com/", 1)[-1]

    def put(self, path, body, **kwargs):
        assert kwargs["access"] == "public"
        assert kwargs["token"] == TOKEN
        self.files[path] = body

    def delete(self, url, **kwargs):
        self.files.pop(self._path(url), None)

    def head(self, url, **kwargs):
        if self._path(url) not in self.files:
            raise BlobNotFoundError()
        return type("Head", (), {"size": len(self.files[self._path(url)])})()


class VercelBlobStorageTests(TestCase):
    def setUp(self):
        self.service = FakeBlobService()
        self.patches = [
            patch("vercel.blob.put", self.service.put),
            patch("vercel.blob.delete", self.service.delete),
            patch("vercel.blob.head", self.service.head),
            patch.dict("os.environ", {"BLOB_READ_WRITE_TOKEN": TOKEN}),
        ]
        for p in self.patches:
            p.start()
        self.storage = VercelBlobStorage()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def test_save_url_exists_delete(self):
        name = self.storage.save("rooms/photo.png", SimpleUploadedFile("photo.png", _png_bytes()))
        self.assertRegex(name, r"^rooms/photo-[0-9a-f]{8}\.png$")
        self.assertIn(f"media/{name}", self.service.files)
        self.assertEqual(
            self.storage.url(name),
            f"https://AbC123Store.public.blob.vercel-storage.com/media/{name}",
        )
        self.assertTrue(self.storage.exists(name))
        self.storage.delete(name)
        self.assertFalse(self.storage.exists(name))

    def test_long_names_fit_the_field(self):
        name = self.storage.get_available_name("gallery/" + "x" * 200 + ".jpeg", max_length=100)
        self.assertLessEqual(len(name), 100)
        self.assertTrue(name.startswith("gallery/") and name.endswith(".jpeg"))

    def test_model_image_upload_goes_to_blob(self):
        field = Residency._meta.get_field("main_image")
        with patch.object(field, "storage", self.storage):
            residency = Residency.objects.create(
                residency_name="Sea View",
                provider_name="Test",
                location="Chennai",
                main_image=SimpleUploadedFile("front.png", _png_bytes(), content_type="image/png"),
            )
            self.assertIn(f"media/{residency.main_image.name}", self.service.files)
            self.assertTrue(residency.main_image.url.startswith("https://AbC123Store.public."))
            residency.main_image.delete(save=False)
        self.assertEqual(self.service.files, {})
