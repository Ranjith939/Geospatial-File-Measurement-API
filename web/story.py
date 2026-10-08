"""Data for the landing page's scroll story, computed by the real pipeline.

The story is told with two bundled samples: survey.zip (one surveyed parcel) and land_parcels.zip
(198 parcels, 2 invalid). Each is processed through process_upload() once and kept with
is_sample=True, so every number the story shows is a backend result, not an illustration.
"""

import math
from pathlib import Path

from django.conf import settings
from pyproj import CRS, Transformer
from shapely.geometry import shape

from core.models import GeoFile
from processing.services import crs_manager
from processing.services.pipeline import process_upload

SAMPLES = Path(settings.BASE_DIR) / "sample-data"
STORY_SAMPLES = ("survey.zip", "land_parcels.zip", "line.kml")


def sample_file(name: str) -> GeoFile | None:
    """The processed sample, processing it on first use. None if the sample file is absent."""
    found = GeoFile.objects.filter(is_sample=True, original_filename=name).first()
    if found or not (SAMPLES / name).exists():
        return found
    file_type = "KML" if name.endswith(".kml") else "SHAPEFILE"
    return process_upload(SAMPLES / name, name, file_type, is_sample=True)


def _graticule(mcrs: CRS, lat_sign: int) -> dict:
    """Meridians/parallels around the UTM zone, in degrees and in the zone's projected metres."""
    op = mcrs.coordinate_operation
    cm = next((p.value for p in (op.params if op else []) if "Longitude" in p.name), 0)  # central meridian
    to_utm = Transformer.from_crs(4326, mcrs, always_xy=True)
    # Wider than the zone itself (±15°, latitudes 0-60°): transverse Mercator's distortion grows away
    # from the central meridian, which is exactly what the scene needs to show.
    lats = [lat_sign * v for v in range(0, 61, 10)]
    lons = [cm + d for d in range(-15, 16, 3)]
    lines = [[(lon, lat_sign * t) for t in range(0, 61, 2)] for lon in lons]
    lines += [[(cm - 15 + t * 0.5, lat) for t in range(0, 61)] for lat in lats]
    proj = [[[round(c, 1) for c in to_utm.transform(lon, lat)] for lon, lat in line] for line in lines]
    return {"central_meridian": cm, "degrees": lines, "metres": proj, "meridians": len(lons)}


def story_context() -> dict | None:
    survey, parcels, line = (sample_file(n) for n in STORY_SAMPLES)
    if survey is None or parcels is None:
        return None
    poly = survey.features.filter(status="success", geometry_type="Polygon").first()
    if poly is None:
        return None

    geom = shape(poly.geometry)
    mcrs = CRS.from_user_input(poly.measurement_crs)
    projected = crs_manager.transform(geom, crs_manager.WGS84, mcrs)
    lat = geom.centroid.y
    road = line.features.filter(geometry_type="LineString", status="success").first() if line else None
    statuses = list(parcels.features.values_list("status", flat=True))
    failed = list(parcels.features.exclude(status="success").values("feature_index", "error_message"))

    return {
        "survey": {
            "file_id": survey.pk,
            "filename": survey.original_filename,
            "size": survey.file_size,
            "components": survey.components,
            "source_crs": survey.source_crs,
            "vertices": [list(map(lambda v: round(v, 7), p)) for p in geom.exterior.coords][:-1],
            "vertices_m": [list(map(lambda v: round(v, 2), p)) for p in projected.exterior.coords][:-1],
            "area_m2": poly.measurement_value,
            "geodesic_m2": poly.geodesic_value,
            "area_deg2": geom.area,  # what a naive planar calculation in degrees would return
            "measurement_crs": poly.measurement_crs,
            "measurement_crs_name": poly.measurement_crs_name,
            "properties": poly.properties,
            "centroid": [round(geom.centroid.x, 6), round(lat, 6)],
            # Ground length of one degree of longitude: at the equator, at this parcel, and at 60°.
            "deg_lon_m": {str(a): round(111_320 * math.cos(math.radians(a))) for a in (0, round(lat, 2), 60)},
        },
        "graticule": _graticule(mcrs, 1 if lat >= 0 else -1),
        "line": {"name": road.properties.get("name"), "length_m": road.measurement_value,
                 "geometry": road.geometry} if road else None,
        "parcels": {
            "file_id": parcels.pk,
            "filename": parcels.original_filename,
            "feature_count": parcels.feature_count,
            "successful": parcels.successful_count,
            "failed": parcels.failed_count,
            "statuses": statuses,
            "failures": [{"feature_id": f["feature_index"] + 1, "error": f["error_message"]} for f in failed],
            "bounds": parcels.bounds,
            "outlines": [f.geometry["coordinates"][0] if f.geometry and f.geometry["type"] == "Polygon" else None
                         for f in parcels.features.only("geometry")],
        },
    }
