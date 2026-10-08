import pytest
from pyproj import CRS
from shapely.geometry import Polygon, box

from processing.services import crs_manager


@pytest.mark.parametrize("lon,lat,epsg", [
    (77.59, 12.97, 32643),   # Bengaluru, UTM 43N
    (-0.12, 51.5, 32630),    # London, 30N
    (151.2, -33.87, 32756),  # Sydney, 56S
    (-180, 0, 32601),
    (180, 0, 32660),
    (10, 86, 32661),         # UPS North
    (10, -85, 32761),        # UPS South
])
def test_utm_zone_selection(lon, lat, epsg):
    assert crs_manager.utm_crs(lon, lat).to_epsg() == epsg


def test_geographic_source_is_projected_before_measuring():
    poly = box(77.5, 12.9, 77.51, 12.91)
    assert crs_manager.measurement_crs_for(poly, CRS.from_epsg(4326)).to_epsg() == 32643


def test_suitable_projected_source_is_kept():
    utm = CRS.from_epsg(32643)
    assert crs_manager.measurement_crs_for(box(77.5, 12.9, 77.51, 12.91), utm) is utm


def test_web_mercator_is_not_used_for_measurement():
    # EPSG:3857 is projected but inflates areas by 1/cos²(lat); it must be replaced by UTM.
    chosen = crs_manager.measurement_crs_for(box(10, 59.9, 10.01, 59.91), CRS.from_epsg(3857))
    assert chosen.to_epsg() == 32632


def test_supported_crs_kinds():
    assert crs_manager.is_supported(CRS.from_epsg(4326))
    assert crs_manager.is_supported(CRS.from_epsg(32643))
    assert not crs_manager.is_supported(CRS.from_epsg(4978))  # geocentric


def test_describe():
    info = crs_manager.describe(CRS.from_epsg(32643))
    assert info.code == "EPSG:32643" and info.type == "projected" and info.units == "metre"
    assert crs_manager.describe(CRS.from_epsg(4326)).type == "geographic"


def test_transform_round_trip():
    poly = Polygon([(777000, 1432000), (778000, 1432000), (778000, 1433000), (777000, 1432000)])
    there = crs_manager.transform(poly, CRS.from_epsg(32643), CRS.from_epsg(4326))
    back = crs_manager.transform(there, CRS.from_epsg(4326), CRS.from_epsg(32643))
    assert back.area == pytest.approx(poly.area, rel=1e-9)
