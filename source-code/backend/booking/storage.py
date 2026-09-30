"""Django file storage backed by Vercel Blob (free on the Hobby plan).

Used for uploaded images (rooms, residencies, gallery, profile photos) when the
BLOB_READ_WRITE_TOKEN environment variable is set. Vercel adds that variable
automatically when a Blob store is connected to the project. Without it, the
app keeps saving uploads to the local media/ folder, so local development is
unchanged.
"""
import os
import posixpath
import secrets

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


def _store_id_from_token(token):
    # Read-write tokens look like "vercel_blob_rw_<storeId>_<secret>".
    # Same rule the official SDK uses.
    parts = token.split("_")
    return parts[3] if len(parts) > 3 else ""


@deconstructible
class VercelBlobStorage(Storage):
    def __init__(self, token=None, base_url=None, location="media"):
        self._token = token
        self._base_url = base_url
        self.location = location.strip("/")

    @property
    def token(self):
        token = self._token or os.getenv("BLOB_READ_WRITE_TOKEN", "")
        if not token:
            raise RuntimeError(
                "BLOB_READ_WRITE_TOKEN is not set. Connect a Vercel Blob store to "
                "the project (Vercel -> Storage -> Blob) and redeploy."
            )
        return token

    @property
    def base_url(self):
        base_url = self._base_url or os.getenv("BLOB_BASE_URL", "")
        if base_url:
            return base_url.rstrip("/")
        store_id = _store_id_from_token(self.token)
        if not store_id:
            raise RuntimeError(
                "Could not work out the Blob store address from "
                "BLOB_READ_WRITE_TOKEN. Set BLOB_BASE_URL to the store's public URL, "
                "e.g. https://abc123.public.blob.vercel-storage.com"
            )
        return f"https://{store_id}.public.blob.vercel-storage.com"

    def _full_path(self, name):
        name = name.replace("\\", "/").lstrip("/")
        return f"{self.location}/{name}" if self.location else name

    def get_available_name(self, name, max_length=None):
        # Give every upload a unique name so files never overwrite each other,
        # while staying within the model field's max_length (100 by default).
        directory, filename = posixpath.split(name.replace("\\", "/"))
        stem, ext = posixpath.splitext(filename)
        token = secrets.token_hex(4)
        if max_length:
            room = max_length - len(directory) - len(ext) - len(token) - 2
            stem = stem[: max(room, 1)]
        filename = f"{stem}-{token}{ext}"
        return posixpath.join(directory, filename) if directory else filename

    def _save(self, name, content):
        from vercel.blob import put

        if hasattr(content, "seek"):
            content.seek(0)
        body = content.read()
        content_type = getattr(content, "content_type", None) or getattr(
            getattr(content, "file", None), "content_type", None
        )
        put(
            self._full_path(name),
            body,
            access="public",
            content_type=content_type,
            add_random_suffix=False,
            overwrite=True,
            cache_control_max_age=60 * 60 * 24 * 365,
            token=self.token,
        )
        return name

    def _open(self, name, mode="rb"):
        from django.core.files.base import ContentFile
        from vercel.blob import get

        result = get(self.url(name), token=self.token)
        data = getattr(result, "content", None)
        if data is None and hasattr(result, "read"):
            data = result.read()
        return ContentFile(data or b"", name=name)

    def delete(self, name):
        if not name:
            return
        from vercel.blob import BlobNotFoundError, delete

        try:
            delete(self.url(name), token=self.token)
        except BlobNotFoundError:
            pass

    def exists(self, name):
        from vercel.blob import BlobNotFoundError, head

        try:
            head(self.url(name), token=self.token)
            return True
        except BlobNotFoundError:
            return False

    def url(self, name):
        return f"{self.base_url}/{self._full_path(name)}"

    def size(self, name):
        from vercel.blob import head

        return head(self.url(name), token=self.token).size
