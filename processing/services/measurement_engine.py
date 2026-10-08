"""Measures in a projected CRS, and I also work out the geodesic value to double check it."""

from dataclasses import dataclass

from pyproj import CRS, Geod
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

from processing.services import crs_manager

GEOD = Geod(ellps="WGS84")
AREAL = {"Polygon", "MultiPolygon"}
LINEAR = {"LineString", "MultiLineString", "LinearRing"}
POINTS = {"Point", "MultiPoint"}


@dataclass
class Measurement:
    measurement_status: str  # measured | not_required | unsupported | failed
    measurement_type: str | None = None  # area | length
    value: float | None = None  # m2 or m
    unit: str | None = None
    geodesic_value: float | None = None
    measurement_crs: CRS | None = None
    error: tuple[str, str] | None = None


def kind_of(geometry_type: str | None) -> str:
    if geometry_type in AREAL:
        return "area"
    if geometry_type in LINEAR:
        return "length"
    if geometry_type in POINTS:
        return "none"
    return "unsupported"


def check_geometry(geom: BaseGeometry) -> tuple[str, str] | None:
    if geom.is_empty:
        return ("EMPTY_GEOMETRY", "Geometry is empty")
    if not geom.is_valid:
        return ("INVALID_GEOMETRY", f"Invalid geometry: {explain_validity(geom)}")
    return None


def measure(projected: BaseGeometry, crs: CRS, geom_wgs84: BaseGeometry | None) -> Measurement:
    """Measures a geometry that's already projected. I use `geom_wgs84` for the geodesic double check."""
    kind = kind_of(projected.geom_type)
    if kind == "none":
        return Measurement("not_required")
    if kind == "unsupported":
        return Measurement("unsupported", error=(
            "UNSUPPORTED_GEOMETRY", f"{projected.geom_type} is not supported for measurement"))

    k = crs_manager.metres_per_unit(crs)
    if kind == "area":
        value = projected.area * k * k
        geodesic = abs(GEOD.geometry_area_perimeter(geom_wgs84)[0]) if geom_wgs84 is not None else None
        return Measurement("measured", "area", round(value, 4), "m2", _r(geodesic), crs)
    value = projected.length * k
    geodesic = GEOD.geometry_length(geom_wgs84) if geom_wgs84 is not None else None
    return Measurement("measured", "length", round(value, 4), "m", _r(geodesic), crs)


def _r(v: float | None) -> float | None:
    return None if v is None else round(v, 4)
