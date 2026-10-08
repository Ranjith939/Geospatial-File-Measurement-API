"""Upload validation tests. When we reject an upload it should return the error envelope and save nothing."""
from core.models import GeoFile
from core.testing import SAMPLES


def code(r):
    return r.json()["error"]["code"]


def test_valid_kml_upload(upload):
    r = upload("polygon.kml")
    assert r.status_code == 201
    assert r.json()["status"] == "completed" and r.json()["file_type"] == "KML"


def test_valid_shapefile_zip_upload(upload):
    r = upload("valid_shapefile.zip")
    assert r.status_code == 201
    assert r.json()["file_type"] == "SHAPEFILE" and r.json()["format"] == "ESRI Shapefile"
    assert {c["name"] for c in r.json()["components"]} >= {"parcels/parcels.shp", "parcels/parcels.shx", "parcels/parcels.dbf"}


def test_unsupported_extension(upload):
    r = upload("data.geojson", b'{"type": "FeatureCollection"}')
    assert r.status_code == 415 and code(r) == "UNSUPPORTED_FILE_TYPE"
    assert not GeoFile.objects.exists()


def test_empty_upload(upload):
    r = upload("empty.kml", b"")
    assert r.status_code in (400, 422)
    assert code(r) in ("EMPTY_FILE", "NO_FILE")


def test_missing_file_field(client, db):
    r = client.post("/api/files/", {}, format="multipart")
    assert r.status_code == 400 and code(r) == "NO_FILE"


def test_oversized_upload(upload):
    r = upload("big.kml", b"<kml>" + b" " * (3 * 1024 * 1024) + b"</kml>")  # tests use a 2 MB limit
    assert r.status_code == 413 and code(r) == "FILE_TOO_LARGE"


def test_corrupt_zip(upload):
    r = upload("corrupt.zip")
    assert r.status_code == 422 and code(r) == "CORRUPT_ARCHIVE"


def test_zip_extension_but_not_a_zip(upload):
    r = upload("fake.zip", b"this is plain text")
    assert r.status_code == 422 and code(r) == "CORRUPT_ARCHIVE"


def test_filename_is_sanitised(upload):
    r = upload("../../etc/parcels v2.kml", (SAMPLES / "point.kml").read_bytes())
    assert r.status_code == 201 and r.json()["filename"] == "parcels v2.kml"
    assert ".." not in GeoFile.objects.get().stored_filename
