"""Fixtures I share across the unit and API tests. The browser tests have their own in e2e/."""
import os

import pytest

# I had to allow this so the ORM works inside pytest-playwright's event loop. Only the browser tests need it.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")


@pytest.fixture
def client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def upload(client, db):
    from core.testing import SAMPLES

    def _upload(name: str, content: bytes | None = None):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = content if content is not None else (SAMPLES / name).read_bytes()
        return client.post("/api/files/", {"file": SimpleUploadedFile(name, data)}, format="multipart")
    return _upload


@pytest.fixture
def measurements(client, upload):
    """Uploads a sample and gives back (file_json, {feature name or source_id: feature measurement})."""
    def _m(name: str, content: bytes | None = None):
        r = upload(name, content)
        assert r.status_code == 201, r.content
        body = client.get(f"/api/files/{r.json()['id']}/measurements/").json()
        by_key = {m["properties"].get("name") or m["source_id"]: m for m in body["features"]}
        return r.json(), by_key
    return _m
