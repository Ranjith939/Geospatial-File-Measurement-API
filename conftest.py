"""Shared pytest fixtures for the unit/API suites (the browser suite adds its own in e2e/)."""
import os

import pytest

# Let the ORM run inside pytest-playwright's sync event loop (browser tests only).
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
    """Upload a sample and return (file_json, {feature name or source_id: feature measurement})."""
    def _m(name: str, content: bytes | None = None):
        r = upload(name, content)
        assert r.status_code == 201, r.content
        body = client.get(f"/api/files/{r.json()['id']}/measurements/").json()
        by_key = {m["properties"].get("name") or m["source_id"]: m for m in body["features"]}
        return r.json(), by_key
    return _m
