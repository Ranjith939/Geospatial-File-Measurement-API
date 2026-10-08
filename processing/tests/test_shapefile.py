import zipfile

import pytest
from pyproj import CRS

from core.testing import SAMPLES, make_zip


def test_projected_shapefile_measured_in_source_crs(measurements):
    f, m = measurements("valid_shapefile.zip")
    assert f["status"] == "completed" and f["format"] == "ESRI Shapefile"
    assert f["source_crs"]["code"] == "EPSG:32643" and f["source_crs"]["type"] == "projected"
    assert f["measurement_crs"] == ["EPSG:32643"]
    assert f["layers"] == ["parcels"]
    areas = {v["properties"]["parcel_id"]: v["measurement"]["area_m2"] for v in m.values()}
    assert areas == {"P-001": 200_000.0, "P-002": 100_000.0, "P-003": 90_000.0}  # exact: no reprojection
    assert m["0"]["properties"]["owner"] == "A. Rao"
    assert f["totals"]["area_ha"] == pytest.approx(39.0)


def test_wgs84_shapefile_lines(measurements):
    f, m = measurements("roads_wgs84.zip")
    assert f["source_crs"]["code"] == "EPSG:4326"
    lengths = {v["properties"]["name"]: v["measurement"]["length_m"] for v in m.values()}
    assert lengths["Ring Rd"] == pytest.approx(2000, rel=1e-6)
    assert lengths["Link Rd"] == pytest.approx(1000, rel=1e-6)  # 500 + 500 (3-4-5 triangle leg)


def test_missing_crs(measurements):
    f, m = measurements("missing_crs.zip")
    assert f["source_crs"] is None and f["crs"] is None
    assert f["status"] == "completed_with_errors" and f["failed_count"] == 3
    assert any("CRS information unavailable" in w for w in f["warnings"])
    assert all(v["error_code"] == "MISSING_CRS" and v["measurement"] is None for v in m.values())
    assert all(v["geometry"] is not None and v["geometry_crs"] is None for v in m.values())  # still inspectable


def _with_prj(prj: bytes) -> bytes:
    with zipfile.ZipFile(SAMPLES / "valid_shapefile.zip") as zf:
        members = {n: zf.read(n) for n in zf.namelist() if not n.endswith(".prj")}
    return make_zip({**members, "parcels/parcels.prj": prj})


def test_invalid_crs(measurements):
    f, m = measurements("badprj.zip", _with_prj(b"this is not a projection"))
    assert f["crs"] is None
    assert all(v["error_code"] == "INVALID_CRS" for v in m.values())
    assert any(".prj file could not be interpreted" in w for w in f["warnings"])


def test_unsupported_crs(measurements):
    # A local site grid: metric, but not tied to the Earth, so it cannot be placed or reprojected.
    site_grid = b'LOCAL_CS["Site grid",LOCAL_DATUM["Site",0],UNIT["metre",1],AXIS["X",EAST],AXIS["Y",NORTH]]'
    f, m = measurements("sitegrid.zip", _with_prj(site_grid))
    assert {v["error_code"] for v in m.values()} == {"UNSUPPORTED_CRS"}
    assert all(v["status"] == "failed" and v["geometry"] is not None for v in m.values())


def test_corrupt_shp_content_fails_file(upload):
    r = upload("garbage.zip", make_zip({"g.shp": b"\x00" * 50, "g.shx": b"\x00" * 50, "g.dbf": b"\x00" * 50}))
    assert r.status_code == 201
    assert r.json()["status"] == "failed" and r.json()["error_code"] == "UNREADABLE_SHAPEFILE"


def test_survey_parcel_matches_its_surveyed_area(measurements):
    """The landing story's subject: measured in UTM 43N after reprojection from WGS84."""
    f, m = measurements("survey.zip")
    (parcel,) = m.values()
    assert f["crs"] == "EPSG:4326" and parcel["measurement_crs"] == "EPSG:32643"
    assert parcel["value"] == pytest.approx(parcel["properties"]["survey_m2"], abs=0.5)
    assert {c["name"] for c in f["components"]} == {f"survey.{e}" for e in ("shp", "shx", "dbf", "prj", "cpg")}
