"""CRS detection and measurement-CRS selection.

Rule: never measure in degrees. A projected source CRS is used as-is when it is fit for
measurement; anything geographic (or a projection that distorts area/length badly, such as
Web Mercator) is measured in the UTM zone of the feature's centroid.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

WGS84 = CRS.from_epsg(4326)  # one shared object, so the identity caches hit
# Projections that are "projected" in name only for measuring purposes.
_UNFIT_METHODS = ("Popular Visualisation Pseudo Mercator", "Mercator", "Equidistant Cylindrical", "Miller")


@dataclass(frozen=True)
class CRSInfo:
    code: str  # "EPSG:4326", or the authority string / WKT name when no code exists
    name: str
    type: str  # geographic | projected | other
    units: str | None

    def as_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "type": self.type, "units": self.units}


def _per_object(fn):
    """Cache fn(crs) by object identity. CRS lookups (to_epsg, to_wkt) cost ~1 ms each and would
    otherwise run once per feature; a file's features share a handful of CRS objects."""
    cache: dict[int, tuple] = {}

    def wrapper(crs):
        hit = cache.get(id(crs))
        if hit is not None and hit[0] is crs:
            return hit[1]
        if len(cache) > 512:  # bounded: objects from finished uploads are dropped wholesale
            cache.clear()
        value = fn(crs)
        cache[id(crs)] = (crs, value)  # holding crs keeps its id from being reused while cached
        return value
    return wrapper


@_per_object
def describe(crs: CRS) -> CRSInfo:
    epsg = crs.to_epsg()
    auth = crs.to_authority()
    code = f"EPSG:{epsg}" if epsg else (":".join(auth) if auth else crs.name)
    kind = "geographic" if crs.is_geographic else "projected" if crs.is_projected else "other"
    units = crs.axis_info[0].unit_name if crs.axis_info else None
    return CRSInfo(code=code, name=crs.name, type=kind, units=units)


@_per_object
def is_supported(crs: CRS) -> bool:
    """Geographic or projected 2D CRSs only; geocentric, engineering or vertical CRSs are refused."""
    return (crs.is_geographic or crs.is_projected) and not crs.is_geocentric


def crs_key(crs: CRS) -> str:
    return describe(crs).code


@_per_object
def _fit_for_measurement(crs: CRS) -> bool:
    if not crs.is_projected:
        return False
    method = crs.coordinate_operation.method_name if crs.coordinate_operation else ""
    if "Transverse Mercator" not in method and any(m in method for m in _UNFIT_METHODS):
        return False
    return bool(crs.axis_info) and crs.axis_info[0].unit_conversion_factor > 0


@lru_cache(maxsize=128)
def _epsg(code: int) -> CRS:
    return CRS.from_epsg(code)


def utm_crs(lon: float, lat: float) -> CRS:
    # ponytail: plain 6° zones; ignores the Norway/Svalbard exceptions and splits features
    # that straddle a zone edge into one zone. Fine for parcel-scale data; continental extents
    # would want an equal-area CRS (e.g. EPSG:6933) instead.
    if lat >= 84:
        return _epsg(32661)  # UPS North
    if lat <= -80:
        return _epsg(32761)  # UPS South
    zone = min(int((lon + 180) // 6) + 1, 60)
    return _epsg((32600 if lat >= 0 else 32700) + zone)


_wkt = _per_object(lambda crs: crs.to_wkt())


@lru_cache(maxsize=256)
def _transformer(src_wkt: str, dst_wkt: str) -> Transformer:
    return Transformer.from_crs(CRS.from_wkt(src_wkt), CRS.from_wkt(dst_wkt), always_xy=True)


def transform(geom: BaseGeometry, src: CRS, dst: CRS) -> BaseGeometry:
    if src is dst or _wkt(src) == _wkt(dst):
        return geom
    t = _transformer(_wkt(src), _wkt(dst))

    def fn(coords: np.ndarray) -> np.ndarray:
        x, y = t.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    out = shapely.transform(geom, fn)
    if not np.isfinite(shapely.get_coordinates(out)).all():
        raise ValueError("Coordinates could not be transformed (outside the CRS area of use)")
    return out


def measurement_crs_for(geom_wgs84: BaseGeometry, src: CRS) -> CRS:
    if _fit_for_measurement(src):
        return src
    c = geom_wgs84.centroid
    return utm_crs(c.x, c.y)


def metres_per_unit(crs: CRS) -> float:
    return crs.axis_info[0].unit_conversion_factor
