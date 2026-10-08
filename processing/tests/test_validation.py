"""Content validation tests. We never trust the file extension by itself."""
from processing.services.file_validator import sanitize_filename
from core.testing import kml


def code(r):
    return r.json()["error"]["code"]


def test_kml_not_xml(upload):
    r = upload("bad.kml", b"not xml at all <<<")
    assert r.status_code == 422 and code(r) == "INVALID_KML"


def test_xml_that_is_not_kml(upload):
    r = upload("other.kml", b"<?xml version='1.0'?><gpx></gpx>")
    assert r.status_code == 422 and code(r) == "INVALID_KML"


def test_kml_entity_declarations_rejected(upload):
    bomb = b'<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY a "aaaa">]><kml>&a;</kml>'
    r = upload("bomb.kml", bomb)
    assert r.status_code == 422 and code(r) == "INVALID_KML"


def test_kml_without_features_fails(upload):
    r = upload("empty_doc.kml", kml("<name>nothing here</name>"))
    assert r.status_code == 201
    assert r.json()["status"] == "failed" and r.json()["error_code"] == "NO_FEATURES"


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename(r"C:\Users\x\land parcels (v2).zip") == "land parcels _v2_.zip"
    assert sanitize_filename("") == "upload"
