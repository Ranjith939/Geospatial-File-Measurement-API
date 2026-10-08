"""The pipeline:

    validate -> extract -> parse -> detect CRS -> validate geometry -> select measurement CRS
             -> transform -> measure -> store

Everything runs inside the upload request, no background jobs. I record how long each stage really
took and keep the file's status on whatever stage is running, so clients can see exactly what
happened. Every per-feature step runs on its own, so if one feature fails the others carry on.
"""

import logging
import shutil
import tempfile
import time
import uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import shapely
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pyproj import CRS
from shapely.geometry.base import BaseGeometry

from core.exceptions import GeoMeasureError
from core.logging import log_event
from core.models import Feature, GeoFile
from processing.services import crs_manager, measurement_engine
from processing.services.archive_processor import extract_shapefiles
from processing.services.file_validator import validate_content
from processing.services.geospatial_reader import RawFeature, read_kml, read_shapefile

WGS84 = crs_manager.WGS84
STATUS_FOR_STAGE = {
    "parsing": GeoFile.Status.PARSING,
    "detecting_crs": GeoFile.Status.DETECTING_CRS,
    "transforming": GeoFile.Status.TRANSFORMING,
    "measuring": GeoFile.Status.MEASURING,
}


class StageClock:
    def __init__(self):
        self.stages: list[dict] = []
        self.file: GeoFile | None = None

    @contextmanager
    def __call__(self, stage: str):
        if self.file is not None and stage in STATUS_FOR_STAGE:
            GeoFile.objects.filter(pk=self.file.pk).update(status=STATUS_FOR_STAGE[stage])
        start = time.perf_counter()
        entry = {"stage": stage, "status": "running", "duration_ms": None}
        self.stages.append(entry)
        try:
            yield
            entry["status"] = "done"
        except Exception:
            entry["status"] = "failed"
            raise
        finally:
            entry["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            log_event(f"stage_{stage}", file_id=self.file.pk if self.file else None, processing_stage=stage,
                      status=entry["status"], duration_ms=entry["duration_ms"])

    def skip(self, stage: str) -> None:
        self.stages.append({"stage": stage, "status": "skipped", "duration_ms": 0})


@dataclass
class Work:
    raw: RawFeature
    geom: BaseGeometry | None = None  # 2D source geometry
    kind: str = "none"  # area | length | none | unsupported
    display: BaseGeometry | None = None  # WGS84, or the raw source coordinates if we can't use the CRS
    wgs84: BaseGeometry | None = None
    mcrs: CRS | None = None
    projected: BaseGeometry | None = None
    result: measurement_engine.Measurement | None = None
    error: tuple[str, str] | None = None

    def fail(self, code: str, message: str) -> None:
        if self.error is None:
            self.error = (code, message)

    @property
    def measurable(self) -> bool:
        return self.error is None and self.kind in ("area", "length")


def process_upload(upload: Path, original_name: str, file_type: str, is_sample: bool = False) -> GeoFile:
    """Validates, processes and saves one upload. If validation fails it raises ValidationFailed before we save anything."""
    clock = StageClock()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="geomeasure-") as work_dir:
        with clock("validating"):
            validate_content(upload, file_type)
        warnings: list[str] = []
        shp_paths: list[Path] = []
        components: list[dict] = [{"name": original_name, "size": upload.stat().st_size}]
        if file_type == GeoFile.FileType.SHAPEFILE:
            with clock("extracting"):
                shp_paths, warnings, components = extract_shapefiles(upload, Path(work_dir))
        else:
            clock.skip("extracting")

        stored = f"{uuid.uuid4().hex}{upload.suffix.lower()}"
        upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(upload, upload_dir / stored)
        geo_file = GeoFile.objects.create(
            original_filename=original_name, stored_filename=stored, file_type=file_type,
            file_size=upload.stat().st_size, status=GeoFile.Status.UPLOADED, components=components,
            is_sample=is_sample,
        )
        clock.file = geo_file
        log_event("file_upload", file_id=geo_file.pk, file_type=file_type, size=geo_file.file_size)

        try:
            _run_pipeline(geo_file, upload, shp_paths, warnings, clock)
        except GeoMeasureError as exc:
            _mark_failed(geo_file, exc.code, exc.message)
        except Exception:
            logging.getLogger("geomeasure").exception("unexpected processing error")
            _mark_failed(geo_file, "PROCESSING_ERROR", "The file could not be processed due to an internal error.")

    geo_file.stages = clock.stages
    geo_file.processed_at = timezone.now()
    geo_file.duration_ms = round((time.perf_counter() - started) * 1000, 2)
    geo_file.save()
    return geo_file


def _mark_failed(geo_file: GeoFile, code: str, message: str) -> None:
    geo_file.status, geo_file.error_code, geo_file.error_message = GeoFile.Status.FAILED, code, message
    log_event("file_processing_failed", logging.ERROR, file_id=geo_file.pk, error_type=code)


def _run_pipeline(geo_file, upload, shp_paths, warnings, clock) -> None:
    with clock("parsing"):
        if geo_file.file_type == GeoFile.FileType.KML:
            raws, layers = read_kml(upload)
        else:
            raws = [f for shp in shp_paths for f in read_shapefile(shp)]
            layers = [p.stem for p in shp_paths]
    geo_file.layers = layers
    works = [Work(raw=r, error=r.error) for r in raws]
    if not works:
        raise GeoMeasureError("NO_FEATURES", "The file contains no features.")

    with clock("detecting_crs"):
        _detect_crs(geo_file, works, warnings)

    steps = [("validating_geometry", _validate_geometry), ("selecting_crs", _select_crs),
             ("transforming", _transform), ("measuring", _measure)]
    for stage, step in steps:
        with clock(stage):
            for w in works:
                _isolated(w, step, geo_file.pk)

    with clock("storing"), transaction.atomic():
        Feature.objects.bulk_create(_summarise(geo_file, works, warnings), batch_size=1000)
    log_event("measurement_complete", file_id=geo_file.pk, features=geo_file.feature_count,
              successful=geo_file.successful_count, failed=geo_file.failed_count)


def _detect_crs(geo_file: GeoFile, works: list[Work], warnings: list[str]) -> None:
    codes = {crs_manager.crs_key(w.raw.crs) if w.raw.crs else None for w in works}
    issues = {w.raw.crs_issue for w in works if w.raw.crs is None}
    if "INVALID_CRS" in issues:
        warnings.append("The .prj file could not be interpreted: measurement cannot be safely calculated.")
    if "MISSING_CRS" in issues:
        warnings.append("CRS information unavailable (no .prj): measurement cannot be safely calculated.")
    unsupported = sorted({crs_manager.crs_key(w.raw.crs) for w in works
                          if w.raw.crs is not None and not crs_manager.is_supported(w.raw.crs)})
    if unsupported:
        warnings.append(f"Unsupported CRS for measurement: {', '.join(unsupported)}.")
    known = sorted(c for c in codes if c)
    if len(known) == 1 and None not in codes:
        geo_file.source_crs = crs_manager.describe(next(w.raw.crs for w in works)).as_dict()
    elif known:
        geo_file.source_crs = {"code": "mixed", "name": ", ".join(known), "type": "mixed", "units": None}


def _isolated(w: Work, step, file_id: int) -> None:
    """Runs one step for one feature. If it throws, the error goes on that feature only, not the whole file."""
    try:
        step(w)
    except Exception as exc:
        w.fail("PROCESSING_ERROR", f"Feature could not be processed: {exc}"[:300])
        log_event("feature_processing_failed", logging.WARNING, file_id=file_id,
                  feature_id=w.raw.source_id, error_type=type(exc).__name__)


def _validate_geometry(w: Work) -> None:
    if w.raw.geometry is None:
        return
    w.geom = shapely.force_2d(w.raw.geometry)
    w.kind = measurement_engine.kind_of(w.geom.geom_type)
    if w.error:
        return
    if w.kind == "unsupported":
        w.fail("UNSUPPORTED_GEOMETRY", f"Measurement not supported for {w.geom.geom_type} geometry")
    elif (problem := measurement_engine.check_geometry(w.geom)) is not None:
        w.fail(*problem)


def _select_crs(w: Work) -> None:
    if not w.measurable:
        return
    src = w.raw.crs
    if src is None:
        w.fail(w.raw.crs_issue or "MISSING_CRS",
               "CRS information unavailable: measurement cannot be safely calculated"
               if w.raw.crs_issue != "INVALID_CRS" else "The CRS (.prj) could not be interpreted")
    elif not crs_manager.is_supported(src):
        w.fail("UNSUPPORTED_CRS", f"{crs_manager.crs_key(src)} is neither geographic nor projected")
    else:
        lon_lat = crs_manager.transform(w.geom.centroid, src, WGS84)
        w.mcrs = crs_manager.measurement_crs_for(lon_lat, src)


def _transform(w: Work) -> None:
    if w.geom is None:
        return
    src = w.raw.crs
    if src is not None and crs_manager.is_supported(src):
        try:
            w.wgs84 = w.display = crs_manager.transform(w.geom, src, WGS84)
        except ValueError as exc:
            w.display = w.geom
            w.fail("TRANSFORM_FAILED", str(exc))
            return
    else:
        w.display = w.geom
    if w.measurable and w.mcrs is not None:
        try:
            w.projected = crs_manager.transform(w.geom, src, w.mcrs)
        except ValueError as exc:
            w.fail("TRANSFORM_FAILED", str(exc))


def _measure(w: Work) -> None:
    if w.error or w.geom is None:
        return
    if w.kind == "none":
        w.result = measurement_engine.Measurement("not_required")
    elif w.projected is not None:
        w.result = measurement_engine.measure(w.projected, w.mcrs, w.wgs84)


def _summarise(geo_file: GeoFile, works: list[Work], warnings: list[str]) -> list[Feature]:
    features, by_status, mcrs_codes = [], Counter(), set()
    area = length = 0.0
    bounds = None
    for i, w in enumerate(works):
        r = w.result
        err = w.error or (None if r else ("MEASUREMENT_FAILED", "Measurement failed"))
        unsupported = bool(err) and err[0] == "UNSUPPORTED_GEOMETRY"
        m_status = "unsupported" if unsupported else "failed" if err else r.measurement_status
        by_status[m_status] += 1
        mcrs = crs_manager.describe(r.measurement_crs) if not err and r.measurement_crs else None
        if mcrs:
            mcrs_codes.add(mcrs.code)
        if not err and r.measurement_type == "area":
            area += r.value
        elif not err and r.measurement_type == "length":
            length += r.value
        if w.display is not None and not w.display.is_empty:
            b = w.display.bounds
            bounds = b if bounds is None else (min(bounds[0], b[0]), min(bounds[1], b[1]),
                                               max(bounds[2], b[2]), max(bounds[3], b[3]))
        features.append(Feature(
            file=geo_file,
            feature_index=i,
            source_id=w.raw.source_id or "",
            layer=w.raw.layer or "",
            geometry_type=w.raw.geometry_type or "",
            geometry=shapely.geometry.mapping(w.display) if w.display is not None else None,
            geometry_crs="EPSG:4326" if w.wgs84 is not None else "",
            properties=w.raw.properties,
            source_crs=crs_manager.crs_key(w.raw.crs) if w.raw.crs else "",
            measurement_crs=mcrs.code if mcrs else "",
            measurement_crs_name=mcrs.name if mcrs else "",
            measurement_type=(r.measurement_type or "") if not err else "",
            measurement_value=r.value if not err else None,
            measurement_unit=(r.unit or "") if not err else "",
            geodesic_value=r.geodesic_value if not err else None,
            measurement_status=m_status,
            status=Feature.Status.UNSUPPORTED if unsupported else Feature.Status.FAILED if err else Feature.Status.SUCCESS,
            error_code=err[0] if err else "",
            error_message=err[1] if err else "",
        ))

    failed = sum(f.status != Feature.Status.SUCCESS for f in features)
    geo_file.feature_count = len(features)
    geo_file.successful_count = len(features) - failed
    geo_file.failed_count = failed
    geo_file.measurement_crs = sorted(mcrs_codes)
    geo_file.geometry_types = dict(Counter(w.raw.geometry_type or "None" for w in works))
    geo_file.bounds = list(bounds) if bounds else None
    geo_file.totals = {
        "area_m2": round(area, 4), "area_ha": round(area / 10_000, 6),
        "length_m": round(length, 4), "length_km": round(length / 1000, 6),
        "by_status": dict(by_status),
    }
    geo_file.warnings = warnings
    geo_file.status = GeoFile.Status.COMPLETED if failed == 0 else GeoFile.Status.COMPLETED_WITH_ERRORS
    return features
