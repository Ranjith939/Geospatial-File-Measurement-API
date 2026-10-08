"""Finds the CRS of a feature and picks which CRS we measure in.

My one rule here: we never measure in degrees. If the source CRS is projected and good for
measuring, I use it as it is. Anything geographic, or a projection that badly distorts area or
length (Web Mercator for example), gets measured in the UTM zone of the feature's centroid.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry

WGS84 = CRS.from_epsg(4326)  # I share one object so the id-based caches below get hits
# These are technically projected, but they're useless for measuring, so I treat them like geographic.
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
    """Caches fn(crs) by object id. CRS lookups like to_epsg and to_wkt take about 1 ms each, and without
    this they'd run once per feature. A file's features only share a handful of CRS objects anyway."""
    cache: dict[int, tuple] = {}

    def wrapper(crs):
        hit = cache.get(id(crs))
        if hit is not None and hit[0] is crs:
            return hit[1]
        if len(cache) > 512:  # keep it small, I just throw away everything from older uploads
            cache.clear()
        value = fn(crs)
        cache[id(crs)] = (crs, value)  # I hold on to crs so Python can't reuse its id while it's in the cache
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
    """We only accept 2D geographic or projected CRSs. Geocentric, engineering and vertical ones get refused."""
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
    # I kept this to plain 6° zones on purpose. It ignores the Norway/Svalbard exceptions, and a feature
    # sitting across a zone edge just goes into one zone. That's fine for parcels, but if we ever get
    # continent-sized data we should switch to an equal-area CRS like EPSG:6933.
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
