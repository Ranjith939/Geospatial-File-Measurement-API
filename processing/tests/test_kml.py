import pytest

from core.testing import kml


def test_polygon_kml(measurements):
    f, m = measurements("polygon.kml")
    assert f["status"] == "completed" and f["format"] == "KML"
    assert f["source_crs"]["code"] == "EPSG:4326" and f["source_crs"]["type"] == "geographic"
    a = m["Parcel A"]
    assert a["geometry_type"] == "Polygon" and a["measurement_status"] == "measured"
    assert a["measurement_crs"] == "EPSG:32643"
    assert a["measurement"]["area_m2"] == pytest.approx(1_000_000, rel=1e-6)
    assert a["measurement"]["area_ha"] == pytest.approx(100, rel=1e-6)
    assert a["properties"] == {"name": "Parcel A", "owner": "Survey Dept", "zone": "R1"}
    assert a["source_id"] == "parcel-a"
    assert m["Parcel B"]["measurement"]["area_m2"] == pytest.approx(90_000, rel=1e-6)  # hole subtracted


def test_line_kml(measurements):
    _, m = measurements("line.kml")
    road = m["Service Road"]
    assert road["geometry_type"] == "LineString"
    assert road["measurement"]["length_m"] == pytest.approx(1400, rel=1e-6)
    assert (road["measurement_type"], road["unit"]) == ("length", "m") and road["value"] == pytest.approx(1400, rel=1e-6)


def test_point_kml(measurements):
    f, m = measurements("point.kml")
    p = m["Survey Marker"]
    assert p["measurement"] is None and p["measurement_status"] == "not_required"
    assert p["status"] == "success" and f["status"] == "completed"


def test_kml_folders_become_layers(measurements):
    f, m = measurements("mixed_geometry.kml")
    assert f["layers"] == ["Mixed geometry / Valid", "Mixed geometry / Problems"]
    assert m["Field 1"]["layer"] == "Mixed geometry / Valid"


def test_kml_altitude_ignored_and_multipolygon(measurements):
    sq = "77.0,12.0,500 77.001,12.0,500 77.001,12.001,500 77.0,12.001,500 77.0,12.0,500"
    ring = f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{sq}</coordinates></LinearRing></outerBoundaryIs></Polygon>"
    _, m = measurements("multi.kml", kml(f"<Placemark><name>mp</name><MultiGeometry>{ring}</MultiGeometry></Placemark>"))
    assert m["mp"]["geometry_type"] == "MultiPolygon"
    assert m["mp"]["measurement"]["area_m2"] == pytest.approx(12_000, rel=0.02)  # ~108.6 m x 110.6 m


def test_kml_placemark_without_geometry(measurements):
    f, m = measurements("nogeom.kml", kml("<Placemark><name>empty</name></Placemark>"))
    assert m["empty"]["error_code"] == "NO_GEOMETRY" and f["failed_count"] == 1
