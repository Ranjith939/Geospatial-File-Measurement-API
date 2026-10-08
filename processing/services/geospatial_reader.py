"""Readers that turn a KML file or a Shapefile into library-neutral `RawFeature`s.

A feature whose geometry cannot be built is still returned, with `error` set, so one bad
Placemark or record never takes down the rest of the file.
"""

import math
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import (
    GeometryCollection,
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from core.exceptions import ProcessingFailed
from processing.services import crs_manager

WGS84 = crs_manager.WGS84
KML_GEOMETRY_TAGS = {"Point", "LineString", "LinearRing", "Polygon", "MultiGeometry", "Model", "Track", "MultiTrack"}


@dataclass
class RawFeature:
    layer: str | None
    source_id: str | None
    geometry: BaseGeometry | None
    geometry_type: str | None
    crs: CRS | None
    properties: dict = field(default_factory=dict)
    error: tuple[str, str] | None = None  # (code, message)
    crs_issue: str | None = None  # MISSING_CRS | INVALID_CRS when crs is None


# ---------------------------------------------------------------- KML

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in el if _local(c.tag) == name), None)


def _text(el: ET.Element | None, name: str) -> str | None:
    c = _child(el, name) if el is not None else None
    return c.text.strip() if c is not None and c.text and c.text.strip() else None


def _coords(el: ET.Element | None) -> list[tuple[float, float]]:
    text = _text(el, "coordinates")
    if not text:
        raise ValueError("Missing <coordinates>")
    out = []
    for token in text.replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            raise ValueError(f"Malformed coordinate '{token[:40]}'")
        lon, lat = float(parts[0]), float(parts[1])  # altitude is dropped: measurements are 2D
        if not (math.isfinite(lon) and math.isfinite(lat)) or abs(lon) > 180 or abs(lat) > 90:
            raise ValueError(f"Coordinate out of range '{token[:40]}'")
        out.append((lon, lat))
    return out


def _kml_geometry(el: ET.Element) -> BaseGeometry:
    tag = _local(el.tag)
    if tag == "Point":
        return Point(_coords(el)[0])
    if tag == "LineString":
        return LineString(_coords(el))
    if tag == "LinearRing":
        return LinearRing(_coords(el))
    if tag == "Polygon":
        boundary = _child(el, "outerBoundaryIs")
        outer = _child(boundary, "LinearRing") if boundary is not None else None
        if outer is None:
            raise ValueError("Polygon has no outer boundary")
        holes = [_coords(_child(b, "LinearRing")) for b in el if _local(b.tag) == "innerBoundaryIs"]
        return Polygon(_coords(outer), holes)
    if tag == "MultiGeometry":
        parts = [_kml_geometry(c) for c in el if _local(c.tag) in KML_GEOMETRY_TAGS]
        if not parts:
            raise ValueError("Empty MultiGeometry")
        kinds = {p.geom_type for p in parts}
        if kinds == {"Point"}:
            return MultiPoint(parts)
        if kinds <= {"LineString", "LinearRing"}:
            return MultiLineString([LineString(p.coords) for p in parts])
        if kinds == {"Polygon"}:
            return MultiPolygon(parts)
        return GeometryCollection(parts)
    raise ValueError(f"Unsupported KML geometry <{tag}>")


def _placemark_properties(pm: ET.Element) -> dict:
    props = {}
    for key in ("name", "description"):
        if (v := _text(pm, key)) is not None:
            props[key] = v
    ext = _child(pm, "ExtendedData")
    if ext is not None:
        for el in ext.iter():
            tag = _local(el.tag)
            if tag == "Data" and el.get("name"):
                props[el.get("name")] = _text(el, "value")
            elif tag == "SimpleData" and el.get("name"):
                props[el.get("name")] = el.text.strip() if el.text else None
    return props


def read_kml(path: Path) -> tuple[list[RawFeature], list[str]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ProcessingFailed("INVALID_KML", "The KML could not be parsed.", {"reason": str(exc)}) from None

    features: list[RawFeature] = []
    layers: list[str] = []

    def walk(el: ET.Element, folder: str | None) -> None:
        for child in el:
            tag = _local(child.tag)
            if tag in ("Document", "Folder"):
                name = _text(child, "name")
                path_name = " / ".join(p for p in (folder, name) if p) or None
                walk(child, path_name)
            elif tag == "Placemark":
                if folder and folder not in layers:
                    layers.append(folder)
                features.append(_read_placemark(child, folder))

    walk(root, None)
    return features, layers


def _read_placemark(pm: ET.Element, layer: str | None) -> RawFeature:
    geom_el = next((c for c in pm if _local(c.tag) in KML_GEOMETRY_TAGS), None)
    feat = RawFeature(layer=layer, source_id=pm.get("id"), geometry=None,
                      geometry_type=_local(geom_el.tag) if geom_el is not None else None,
                      crs=WGS84, properties=_placemark_properties(pm))
    if geom_el is None:
        feat.error = ("NO_GEOMETRY", "Placemark has no geometry")
        return feat
    try:
        feat.geometry = _kml_geometry(geom_el)
        feat.geometry_type = feat.geometry.geom_type
    except (ValueError, TypeError, IndexError) as exc:
        code = "UNSUPPORTED_GEOMETRY" if str(exc).startswith("Unsupported") else "INVALID_GEOMETRY"
        feat.error = (code, f"Invalid geometry: {exc}" if code == "INVALID_GEOMETRY" else str(exc))
    return feat


# ---------------------------------------------------------------- Shapefile

def _jsonable(v):
    if v is None:
        return None
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):  # numpy scalar
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, (dt.date, dt.datetime, dt.time)):
        return v.isoformat()
    if hasattr(v, "isoformat"):  # pandas Timestamp
        return None if str(v) == "NaT" else v.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v if isinstance(v, (str, int, float, bool)) else str(v)


def read_shapefile(shp: Path) -> list[RawFeature]:
    try:
        gdf = gpd.read_file(shp, engine="pyogrio")
    except Exception as exc:  # GDAL raises a variety of types for corrupt files
        raise ProcessingFailed(
            "UNREADABLE_SHAPEFILE", f"Shapefile '{shp.name}' could not be read.", {"reason": str(exc)[:300]}
        ) from None

    crs = gdf.crs
    # A .prj that GDAL cannot interpret is not the same failure as no .prj at all.
    crs_issue = None if crs is not None else ("INVALID_CRS" if shp.with_suffix(".prj").exists() else "MISSING_CRS")
    attrs = [c for c in gdf.columns if c != gdf.geometry.name]
    features = []
    for fid, (geom, *values) in enumerate(gdf[[gdf.geometry.name, *attrs]].itertuples(index=False, name=None)):
        feat = RawFeature(layer=shp.stem, source_id=str(fid), geometry=geom,
                          geometry_type=geom.geom_type if geom is not None else None,
                          crs=crs, properties={k: _jsonable(v) for k, v in zip(attrs, values)},
                          crs_issue=crs_issue)
        if geom is None:
            feat.error = ("NO_GEOMETRY", "Record has no geometry")
        features.append(feat)
    return features
