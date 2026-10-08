# GEO/MEASURE: Geospatial File Measurement API

> Spatial data, measured.

![Scroll story: transform the space](docs/screenshots/03_story_transform.png)

## Project Overview

GeoMeasure accepts a **KML** file or a **ZIP containing a Shapefile**, reads it feature by feature, detects
the coordinate reference system, reprojects geographic data into a metric CRS, and measures each feature:
**area** for polygons, **length** for lines. Points need no measurement. Results are stored and served
through a REST API.

The interface explains what the backend does. A scroll-driven story follows one real file through the
pipeline: file → structure → geometry → coordinates → CRS → projected space → measurement → many features
→ failure isolation. It then hands over to the working upload workspace. Every number in the story is a
stored backend result for a bundled sample, not an illustration.

## Assignment Requirements

| Requirement | Where |
|---|---|
| Django + DRF backend | `geomeasure/`, `api/` |
| Accept `.kml` and `.zip` Shapefile | `processing/services/file_validator.py`, `archive_processor.py` |
| Extract features; ID/index, geometry type and geometry, CRS, properties | `processing/services/geospatial_reader.py`, `core/models.py` |
| Polygon → area, LineString → length, Point → not required | `processing/services/measurement_engine.py` |
| Unsupported geometry handled gracefully | `status: "unsupported"`, `UNSUPPORTED_GEOMETRY` |
| Geographic CRS reprojected before measuring | `processing/services/crs_manager.py` |
| `POST /api/files/`, `GET /api/files/{id}/`, `GET /api/files/{id}/measurements/` | `api/views.py` |
| Tests | 64 unit/API tests + 12 browser tests |
| Documentation | this README, `/api-docs/`, Swagger at `/api/docs/` |

## Features

- Upload `.kml` or `.zip`; the content is validated, not just the extension.
- Safe ZIP handling: rejects empty archives, path traversal, absolute paths, symlinks, too many members and zip bombs; extracts only Shapefile components.
- Each feature carries ID and index, source ID, layer, geometry type, GeoJSON geometry, properties, source CRS and measurement CRS.
- CRS handling: geographic → UTM zone of each feature; a fit projected CRS is kept; Web Mercator is never used for measuring; missing, invalid and unsupported CRSs are reported, never guessed.
- Area in m²/ha and length in m/km, plus an ellipsoidal (geodesic) cross-check.
- **Per-feature failure isolation**: one bad feature never fails the file.
- Real processing states and stage timings, stored and exposed.
- UI: ten-scene GSAP ScrollTrigger story, recorded-stage replay, SVG map (pan/zoom, hover, select, fit, dimension lines, graticule, scale bar), feature explorer, Simple/Technical modes, a lazy-loaded Three.js 2.5D inspector, a custom API page with try-request, and Swagger.

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.13, Django 5.2, Django REST Framework, drf-spectacular (OpenAPI/Swagger) |
| Geospatial | GeoPandas + Pyogrio (GDAL) for Shapefiles, a stdlib XML reader for KML, Shapely 2, PyProj |
| Storage | Django ORM; SQLite by default, PostgreSQL in Docker |
| Frontend | Django templates + vanilla ES modules (no build step), GSAP 3.13 + ScrollTrigger, SVG, Three.js 0.186 (lazy) |
| Static | WhiteNoise, hashed and compressed |
| Tests | pytest, pytest-django, pytest-playwright |
| Ops | Docker, docker compose, gunicorn, GitHub Actions |

## Architecture

```text
 Browser ── Django templates + ES modules (story, workspace, API docs)
    │              │ fetch /api/…
    ▼              ▼
 web/ (pages)    api/ (DRF views, serializers, error envelope)
                   │
                   ▼
         processing/services/pipeline.py ──► core/models.py (GeoFile, Feature)
   ┌──────────┬──────────┬──────────────┬──────────────┬────────────────┐
 file_      archive_   geospatial_    crs_manager    measurement_
 validator  processor  reader         (detect, UTM,  engine (planar,
 (type,     (safe      (KML parser,   transform)     geodesic check)
  content)   extract)   GeoPandas)
```

## Repository Structure

```text
geomeasure/            project package: settings, test_settings, urls, wsgi, asgi
core/                  models (GeoFile, Feature), migrations, admin, exceptions, logging, test helpers
processing/            services/ (validator, archive, reader, crs, measurement, pipeline) + tests/
api/                   DRF views, serializers, urls, exception handler + tests/
web/                   page views, story.py (story data from real results), templates/, static/web/
  static/web/js/       api, geo, dom, upload, map-viewer, panels, feature-table, pipeline, inspector, workspace
  static/web/js/story/ index + one module per scene (hero … workspace)
  static/web/vendor/   gsap/, three/ (self-hosted)
  static/web/models/   inspector_stack.glb (generated, see Design Decisions)
e2e/                   Playwright browser tests
sample-data/           deterministic datasets + generator
scripts/benchmark.py   performance measurements
docker/ deploy/        entrypoint, nginx and systemd examples
.github/workflows/     CI
```

## Setup

Requirements: Python 3.12+ (developed on 3.13). Node is **not** required.

Quickest way: `bash run.sh` (or `bash run.sh 8080`). It does the steps below for you and starts the server.

```bash
python -m venv .venv
.venv/Scripts/activate              # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                # set SECRET_KEY, or DEBUG=True for local development
python manage.py migrate
```

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | none (required unless `DEBUG=True`) | Django signing key |
| `DEBUG` | `False` | development mode |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | `localhost,127.0.0.1` / empty | host checks |
| `DATABASE_URL` | `sqlite:///geomeasure.db` | or `postgres://user:pass@host:5432/db` |
| `MEDIA_ROOT` | `./media` | stored uploads (UUID names) |
| `MAX_UPLOAD_MB` / `MAX_EXTRACTED_MB` / `MAX_ARCHIVE_MEMBERS` | 50 / 500 / 1000 | upload and zip-bomb limits |
| `SECURE_SSL` | `False` | HTTPS redirects, secure cookies and HSTS behind a TLS proxy |
| `LOG_LEVEL` | `INFO` | structured log level |
| `POSTGRES_PASSWORD`, `WEB_WORKERS` | none / 2 | docker compose |

## Backend

```bash
python manage.py runserver          # http://127.0.0.1:8000
```

The landing page processes the bundled story samples (`survey.zip`, `land_parcels.zip`, `line.kml`) through
the real pipeline on first visit and keeps them flagged `is_sample` (hidden from the file list).

## Frontend

Served by Django itself: templates in `web/templates/`, ES modules in `web/static/web/js/`, no bundler. GSAP
loads on the landing page only; Three.js loads only when **Inspect 2.5D** is opened, through an import map
whose URLs go through `{% static %}`, so hashed production filenames resolve.

## Docker

```bash
cp .env.example .env                # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build           # http://localhost:8000  (PostgreSQL 17 + gunicorn)
```

The image runs `migrate` on start and serves static files with WhiteNoise. `deploy/` has an nginx site and a
systemd unit for non-container installs.

## API

Swagger UI: `/api/docs/` · OpenAPI schema: `/api/schema/` · custom reference with try-request: `/api-docs/`

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/files/` | upload and process (multipart field `file`) |
| `GET` | `/api/files/{id}/` | file information |
| `GET` | `/api/files/{id}/measurements/` | per-feature measurements (`?status=success\|failed\|unsupported`, `?include_geometry=false`) |
| `GET` | `/api/files/` | recent uploads |
| `DELETE` | `/api/files/{id}/` | remove a file and its features |

```bash
curl -F "file=@sample-data/land_parcels.zip" http://127.0.0.1:8000/api/files/
```

```json
{
  "id": 2, "filename": "land_parcels.zip", "file_type": "SHAPEFILE", "format": "ESRI Shapefile",
  "status": "completed_with_errors", "crs": "EPSG:4326",
  "source_crs": {"code": "EPSG:4326", "name": "WGS 84", "type": "geographic", "units": "degree"},
  "measurement_crs": ["EPSG:32643"],
  "feature_count": 198, "successful_count": 196, "failed_count": 2,
  "totals": {"area_m2": 12799799.0, "area_ha": 1279.9799, "length_m": 0.0, "by_status": {"measured": 196, "failed": 2}},
  "stages": [{"stage": "validating", "status": "done", "duration_ms": 2.18}, "…"]
}
```

```bash
curl "http://127.0.0.1:8000/api/files/2/measurements/?include_geometry=false"
```

```json
{
  "file_id": 2, "status": "completed_with_errors", "crs": "EPSG:4326",
  "feature_count": 198, "successful": 196, "failed": 2,
  "features": [
    {"feature_id": 1, "geometry_type": "Polygon", "status": "success", "measurement_status": "measured",
     "measurement_type": "area", "value": 22500.0, "unit": "m²",
     "source_crs": "EPSG:4326", "measurement_crs": "EPSG:32643", "measurement_crs_name": "WGS 84 / UTM zone 43N",
     "measurement": {"area_m2": 22500.0, "area_ha": 2.25, "geodesic_value": 22475.278, "method": "planar"},
     "properties": {"parcel_no": 1, "village": "Hebbal", "survey_m2": 22500.0}},
    {"feature_id": 83, "geometry_type": "Polygon", "status": "failed", "measurement_status": "failed",
     "measurement": null, "error_code": "INVALID_GEOMETRY",
     "error": "Invalid geometry: Self-intersection[77.5988000407303 12.9600265868654]"}
  ]
}
```

A point returns `"measurement": null, "measurement_status": "not_required"`. An unsupported geometry returns
`"status": "unsupported", "measurement": null, "error": "Measurement not supported for GeometryCollection geometry"`.

## Supported Formats

| Format | Notes |
|---|---|
| `.kml` | KML 2.x: Point, LineString, LinearRing, Polygon (with holes), MultiGeometry. `name`, `description` and `ExtendedData` (`Data`, `SimpleData`) become properties; folder paths become layers; altitude is ignored. CRS is EPSG:4326 by specification. |
| `.zip` | One or more Shapefile sets (`.shp`, `.shx`, `.dbf` required; `.prj`, `.cpg`, indexes optional), at the root or in sub-folders. Other members are never extracted. |

## Processing Flow

```text
validating → extracting → parsing → detecting_crs → validating_geometry → selecting_crs → transforming → measuring → storing
```

1. **validating**: allow-listed extension, non-empty, size limit, content check (well-formed XML with a `<kml>` root and no DOCTYPE/ENTITY; ZIP opens and passes CRC).
2. **extracting**: every member path is checked, then only Shapefile components go into a private temp directory, which is always removed.
3. **parsing**: features become library-neutral `RawFeature`s; a feature that cannot be built keeps its error.
4. **detecting_crs**: the CRS per source; `mixed`, missing, invalid (`.prj` present but unreadable) or unsupported.
5. **validating_geometry**: empty or invalid geometry and unsupported types fail here, per feature.
6. **selecting_crs**: the measurement CRS per feature (below).
7. **transforming**: to WGS84 for display, and to the measurement CRS.
8. **measuring**: planar area or length, plus the geodesic cross-check.
9. **storing**: one bulk insert of features, plus file totals, bounds, components and stage timings.

The file's `status` column follows the stage being run (`parsing`, `detecting_crs`, `transforming`,
`measuring`) and ends `completed`, `completed_with_errors` or `failed`. Validation and extraction failures
reject the upload with a 4xx and store nothing. Later file-level failures (an unreadable `.shp`, no
features) are stored with `status: failed`, so they can still be inspected.

## CRS Strategy

Area and distance are **never** computed in degrees. One degree of longitude is 111.32 km at the
equator, 108.49 km at the sample parcel's latitude (12.94°) and 55.66 km at 60°. The landing story's
scene 05 shows exactly this.

| Source CRS | Measurement CRS |
|---|---|
| Geographic (e.g. EPSG:4326) | UTM zone of the feature's centroid (EPSG:326xx / 327xx; UPS 32661 / 32761 beyond 84°N / 80°S) |
| Projected and fit (UTM, national grids, …) | the source CRS itself; non-metre units are converted with its unit factor |
| Projected but distorting (Web Mercator, Mercator, Plate Carrée, Miller) | UTM, as for geographic |
| Missing (no `.prj`) | none; `MISSING_CRS` on each measurable feature; geometry still shown in source coordinates |
| Invalid (`.prj` unreadable) | none; `INVALID_CRS` |
| Unsupported (e.g. a local site grid, geocentric) | none; `UNSUPPORTED_CRS` |

The zone is chosen per feature, so data spanning zones is measured correctly in each. Every feature
records `source_crs` and `measurement_crs`. Lookups of CRS metadata are cached per CRS object, because
`pyproj` EPSG lookups cost about 1 ms each and would otherwise run once per feature.

## Measurement Methodology

- **Polygon / MultiPolygon**: `shapely.area` in the measurement CRS, holes subtracted → `area_m2`, `area_ha`.
- **LineString / MultiLineString / LinearRing**: `shapely.length` → `length_m`, `length_km`.
- **Point / MultiPoint**: `not_required`.
- **GeometryCollection, unsupported KML elements**: `unsupported`.
- **Validity**: checked with `shapely.is_valid` before measuring. Invalid geometry fails with Shapely's explanation and is not silently repaired, because a repaired shape would report an area the source never described.
- **Geodesic cross-check**: `pyproj.Geod(WGS84)` on the WGS84 geometry, returned as `geodesic_value`. The survey parcel reads 145,337.50 m² planar in UTM 43N and 145,177.44 m² on the ellipsoid, a difference of +0.110%. That is the expected UTM scale distortion 2.6° from the central meridian.

## Error Handling

Every API error has one shape, and no traceback ever reaches a client:

```json
{"error": {"code": "INVALID_SHAPEFILE", "message": "The uploaded ZIP does not contain a valid Shapefile structure.",
           "details": {"expected": [".shp", ".shx", ".dbf"], "missing": {"parcels/parcels": [".shx"]}}}}
```

| HTTP | Codes |
|---|---|
| 400 | `NO_FILE`, `EMPTY_FILE`, `INVALID_REQUEST` (unparseable body) |
| 404 | `FILE_NOT_FOUND`, `NOT_FOUND` |
| 413 | `FILE_TOO_LARGE` |
| 415 | `UNSUPPORTED_FILE_TYPE`, `UNSUPPORTED_MEDIA_TYPE` |
| 422 | `INVALID_KML`, `CORRUPT_ARCHIVE`, `EMPTY_ARCHIVE`, `UNSAFE_ARCHIVE`, `INVALID_SHAPEFILE`, `INVALID_REQUEST` |
| 500 | `INTERNAL_ERROR` (logged server-side with traceback) |

Feature codes: `INVALID_GEOMETRY`, `EMPTY_GEOMETRY`, `NO_GEOMETRY`, `UNSUPPORTED_GEOMETRY`, `MISSING_CRS`,
`INVALID_CRS`, `UNSUPPORTED_CRS`, `TRANSFORM_FAILED`, `PROCESSING_ERROR`. File codes after storage:
`NO_FEATURES`, `UNREADABLE_SHAPEFILE`, `PROCESSING_ERROR`. The UI maps each code to a written error state.

## Failure Isolation

Each per-feature step (validate geometry, select CRS, transform, measure) runs inside `_isolated()` in
`pipeline.py`: any exception becomes that feature's error, never the file's. `land_parcels.zip` has two
self-intersecting parcels at #83 and #141. The result is `completed_with_errors`, with 196 success and 2
failed, and parcels #82 and #84 are measured normally (tested in `test_failures.py`). Failed features keep
their geometry and properties, so the map can show what is wrong.

## Database Design

**GeoFile**: `original_filename, stored_filename, file_type, file_size, status, source_crs (JSON), measurement_crs (JSON list), feature_count, successful_count, failed_count, layers, components, geometry_types, bounds, totals, stages, warnings, is_sample, created_at, processed_at, duration_ms, error_code, error_message`

**Feature**: `file → GeoFile (cascade), feature_index (unique per file), source_id, layer, geometry_type, geometry (GeoJSON), geometry_crs, properties (JSON), source_crs, measurement_crs, measurement_crs_name, measurement_type, measurement_value, measurement_unit, geodesic_value, measurement_status, status, error_code, error_message`

Only the WGS84 display geometry is stored. The projected copy is cheap to recompute and would double the
payload. PostGIS isn't needed for these endpoints (no spatial queries); a `geometry(Geometry, 4326)`
column is the upgrade path if that changes.

## Security

- Extension allow-list plus content validation; client MIME types are not trusted.
- Size limit checked from `Content-Length` and the parsed upload; nginx example sets `client_max_body_size`.
- ZIP: no absolute paths, `..`, drive letters or symlinks; member and expanded-size caps; resolved paths re-checked inside the temp dir; only Shapefile extensions extracted.
- KML: DOCTYPE/ENTITY rejected; ElementTree never resolves external entities.
- Uploads stored under UUID names; original filenames sanitised and only displayed.
- No shell commands; nothing uploaded is executed; temp directories always cleaned.
- Controlled error envelope; tracebacks only in server logs.
- Same-origin UI, so no CORS is enabled and cross-origin browser calls are refused by default. `X-Frame-Options: DENY`, `nosniff`, HTTPS settings behind `SECURE_SSL`.
- Secrets from the environment; `.env` is git-ignored; `DEBUG` defaults to `False` and `SECRET_KEY` is required in production; the container runs as a non-root user.
- Structured logs carry ids, stages, durations and error types, never file contents.

## Testing

| Suite | File | Covers |
|---|---|---|
| API | `api/tests/test_upload.py` | valid KML/ZIP, unsupported extension, empty, missing field, oversized, corrupt and fake ZIP, filename sanitising |
| API | `api/tests/test_api.py` | POST → GET → GET measurements, stage list, filters, list, 404, delete, OpenAPI and Swagger |
| Processing | `processing/tests/test_validation.py` | malformed KML, non-KML XML, entity declarations, KML without features |
| Processing | `processing/tests/test_archive.py` | traversal, absolute path, symlink, empty ZIP, no shapefile, missing `.shx`, only components extracted |
| Processing | `processing/tests/test_kml.py` | polygon (100 ha), holes, line (1,400 m), point, folders → layers, altitude/MultiGeometry, no geometry |
| Processing | `processing/tests/test_shapefile.py` | projected source exact, WGS84 lines, missing/invalid/unsupported CRS, unreadable `.shp`, survey parcel |
| Processing | `processing/tests/test_crs.py` | UTM zones both hemispheres and edges, UPS, Web Mercator refused, kept projected CRS, supported kinds |
| Processing | `processing/tests/test_measurements.py` | area, length, points, collections, US-feet unit conversion, "never degrees", validity |
| Processing | `processing/tests/test_failures.py` | success → failure → success = 2/1; mixed sample; demo 198/196/2 with every area checked |
| Browser | `e2e/test_workspace.py` | upload → recorded stages → results, selection, failed feature, keyboard table, error states, lazy Three.js |
| Browser | `e2e/test_story.py` | 10 scenes / 10 triggers, real values, reduced motion is static, API try-request, no mobile overflow |

## Performance

Measured with `scripts/benchmark.py` through the real API (SQLite, Windows 11, Intel Core with 8 logical
CPUs, Python 3.13). Times in ms; peak is the Python heap only (tracemalloc does not see GDAL's native memory).

| Format | Features | POST total | Parsing | Validate geom | Select CRS | Transform | Measure | Store | GET measurements | Peak MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shapefile | 10 | 215 | 40 | 1 | 1 | 2 | 3 | 21 | 8 | 0.2 |
| KML | 10 | 101 | 5 | 0 | 0 | 3 | 2 | 19 | 7 | 0.1 |
| Shapefile | 100 | 320 | 43 | 2 | 3 | 19 | 19 | 128 | 14 | 0.5 |
| KML | 100 | 280 | 47 | 2 | 2 | 18 | 15 | 112 | 13 | 0.5 |
| Shapefile | 1,000 | 2,048 | 188 | 22 | 29 | 308 | 214 | 1,139 | 93 | 3.1 |
| KML | 1,000 | 1,658 | 373 | 22 | 19 | 195 | 124 | 775 | 80 | 3.5 |
| Shapefile | 10,000 | 10,721 | 807 | 140 | 211 | 1,194 | 795 | 7,305 | 791 | 26.8 |
| KML | 10,000 | 13,684 | 3,082 | 149 | 117 | 1,088 | 1,145 | 7,539 | 718 | 30.3 |

About 1.1 ms per feature end to end. Profiling a 10k upload shows storing dominated by Django model
construction and SQLite's parameter-limited batches. Next steps: write features with a raw multi-row
insert or `COPY` on PostgreSQL, vectorise transforms per CRS group (with per-feature fallback to keep
isolation), and move large files to a background worker. The `status` column and `GET /api/files/{id}/`
already support polling.

Frontend: the map is plain SVG with nodes built once (pan/zoom only touch the `viewBox`); the table renders
100 rows at a time; Three.js and the GLB load only on demand; GSAP only on the landing page; story scenes
animate `transform`, `opacity` and SVG attributes.

## Design Decisions

- **Django + DRF**, in the agrodash project layout: a project package plus focused apps (`core` models, `processing` services, `api`, `web`), templates and per-app static JS. The geo services are framework-free and unit-tested directly.
- **Vanilla JS, no build step**: ES modules served by Django; a small `h()` helper replaces a framework. This means less tooling, and the page works the moment `runserver` starts.
- **Story from real results**: `web/story.py` runs the bundled samples through `process_upload()` and passes stored values to the template. The graticule in scene 06 is reprojected server-side by PyProj, so the deformation is the real UTM projection.
- **One timeline per scene**: each scene module builds its own paused GSAP timeline bound to its own ScrollTrigger (pinned on wide screens, unpinned scrub on narrow ones). There's no global timeline. `prefers-reduced-motion` skips ScrollTrigger and shows every scene's final state.
- **GeoPandas for Shapefiles, own KML reader**: GDAL is robust for the binary format; a ~120-line `ElementTree` reader keeps every Placemark independent (one broken `<coordinates>` fails only that feature) and reads `ExtendedData` without LIBKML.
- **Per-feature UTM, invalid geometry not repaired, synchronous processing with recorded stages**: each is the simplest option that is correct for the target sizes, and each is explained above.
- **SVG map instead of MapLibre**: no tile service or key, no WebGL requirement; the uploaded geometry is the subject. A basemap is the obvious addition if needed.
- **2.5D inspector**: the stack model `web/static/web/models/inspector_stack.glb` was built for this project. It is procedural code in `D:\GLB\js\geomeasure\inspectorModel.js`, exported by `node export_geomeasure.js`, and no existing asset is used. It shows four plates: FILE → CRS (graticule, ticks, north arrow) → GEOMETRY (measuring stage, scale bar) → PROPERTIES. The uploaded feature is extruded onto its `Geometry_Anchor`, labelled "visualization only · not elevation".
- **Originality**: the visual identity (survey paper, ink, forest green, survey amber; Inter + JetBrains Mono), every scene, icon and the GLB were made for GeoMeasure. Nothing visual is reused from CropDesk, TheDotProject, AkashBhumi or other projects; only the repository layout follows agrodash, as requested.

## Limitations

- KMZ, GeoJSON, GPX and GeoPackage are not accepted; KML `gx:Track`, `Model` and NetworkLinks are unsupported.
- UTM zones ignore the Norway/Svalbard exceptions; a feature straddling a zone edge uses its centroid's zone; continental-scale polygons would be better in an equal-area CRS (e.g. EPSG:6933).
- Antimeridian-crossing features are not split.
- Processing is synchronous: a 10,000-feature upload holds its request for about 11 s.
- No authentication: any client can list, read and delete files.
- The PostgreSQL/Docker path is configured and the image definition is in CI, but it was not run on the development machine (no Docker available); the test suites run on SQLite.
- The scroll story needs JavaScript; without it the copy is readable but the stages are empty.

## Future Scope

Background job queue with live status; KMZ/GeoJSON/GeoPackage; equal-area option for large extents;
PostGIS columns and spatial filters; authentication and per-user files; a MapLibre basemap; CSV/GeoJSON export.

## Screenshots/GIF

| | |
|---|---|
| ![Hero](docs/screenshots/01_story_hero.png) 01 Hero | ![File](docs/screenshots/02_story_file.png) 02 The archive opens into its real components |
| ![Measure](docs/screenshots/04_story_measure.png) 07 Measurement with real values | ![Failure](docs/screenshots/05_story_failure.png) 09 Failure isolation (#83) |
| ![Processing](docs/screenshots/06_processing.png) Recorded stage replay | ![Workspace](docs/screenshots/07_workspace_selected.png) Workspace, selected feature |
| ![Failed](docs/screenshots/08_failed_feature.png) Failed feature, technical mode | ![2.5D](docs/screenshots/09_inspector.png) 2.5D inspector, exploded |
| ![Missing CRS](docs/screenshots/10_missing_crs.png) Missing CRS | ![Invalid](docs/screenshots/11_invalid_zip.png) Invalid Shapefile ZIP |
| ![API](docs/screenshots/12_api_docs.png) API reference with try-request | ![Mobile](docs/screenshots/13_mobile.png) Mobile |

## Learning

- "Projected" is not "fit for measuring": Web Mercator is projected and still inflates areas.
- A geodesic cross-check is a cheap correctness alarm: planar UTM and ellipsoidal areas should agree within about 0.1–0.2% inside a zone.
- Robustness is a data-model property: when a feature can carry its own error, one bad record cannot fail the file.
- Honest UI: the story and the replay show stored results and recorded timings; nothing on screen is invented.
- Per-feature `pyproj` metadata calls were the hidden cost at 10k features; caching them by CRS object halved total time.

## Test Commands

```bash
python -m pytest processing api            # 64 unit + API tests
python -m playwright install chromium      # once
python -m pytest e2e                       # 12 browser tests (headless; add --headed to watch)
python manage.py check && python manage.py makemigrations --check --dry-run
python scripts/benchmark.py                # performance table above
python sample-data/generate_samples.py     # regenerate sample data
```
