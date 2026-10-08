import pytest
from pyproj import CRS
from shapely.geometry import GeometryCollection, LineString, MultiPoint, Point, Polygon, box

from processing.services import crs_manager
from processing.services.measurement_engine import check_geometry, measure

UTM = CRS.from_epsg(32643)


def test_polygon_area():
    m = measure(box(0, 0, 100, 50), UTM, None)
    assert (m.measurement_status, m.measurement_type, m.value, m.unit) == ("measured", "area", 5000, "m2")


def test_line_length():
    m = measure(LineString([(0, 0), (3, 4), (3, 10)]), UTM, None)
    assert (m.measurement_type, m.value, m.unit) == ("length", 11, "m")


@pytest.mark.parametrize("geom", [Point(1, 2), MultiPoint([(0, 0), (1, 1)])])
def test_points_need_no_measurement(geom):
    m = measure(geom, UTM, None)
    assert m.measurement_status == "not_required" and m.value is None


def test_geometry_collection_unsupported():
    m = measure(GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])]), UTM, None)
    assert m.measurement_status == "unsupported" and m.error[0] == "UNSUPPORTED_GEOMETRY"


def test_feet_based_crs_is_converted_to_metres():
    ft = CRS.from_epsg(2227)  # NAD83 / California zone 3 (US survey ft)
    m = measure(box(0, 0, 1000, 1000), ft, None)
    assert m.value == pytest.approx(1000 * 1000 * 0.3048006096**2, rel=1e-6)


def test_degrees_are_never_measured_directly():
    """Same 0.01° square both ways. In degrees the 'area' comes out as 1e-4, projected it's about 1.2 km²."""
    sq = box(77.5, 12.9, 77.51, 12.91)
    mcrs = crs_manager.measurement_crs_for(sq, crs_manager.WGS84)
    projected = crs_manager.transform(sq, crs_manager.WGS84, mcrs)
    m = measure(projected, mcrs, sq)
    assert m.value == pytest.approx(1_200_000, rel=0.02)
    assert m.geodesic_value == pytest.approx(m.value, rel=0.002)  # planar UTM should agree with the geodesic value


def test_invalid_geometry_detected():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    assert check_geometry(bowtie)[0] == "INVALID_GEOMETRY"
    assert check_geometry(Polygon())[0] == "EMPTY_GEOMETRY"
    assert check_geometry(box(0, 0, 1, 1)) is None
