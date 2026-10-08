"""Measure processing time for 10 / 100 / 1,000 / 10,000 polygon features.

    .venv/Scripts/python scripts/benchmark.py

Each run uploads a generated WGS84 shapefile ZIP and a KML through the real API (DRF test client,
with a throwaway SQLite DB in a temp dir). It prints the stage timings the server recorded and how
long GET /measurements/ takes. Peak memory comes from tracemalloc, so it's only the Python heap,
GDAL's own native memory isn't counted.
"""

import io
import os
import sys
import tempfile
import time
import tracemalloc
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix="geomeasure-bench-"))
os.environ.update(DJANGO_SETTINGS_MODULE="geomeasure.settings", SECRET_KEY="bench", DEBUG="False",
                  DATABASE_URL=f"sqlite:///{(TMP / 'bench.db').as_posix()}", MEDIA_ROOT=str(TMP / "media"),
                  MAX_UPLOAD_MB="500", LOG_LEVEL="WARNING", ALLOWED_HOSTS="testserver")

import django  # noqa: E402

django.setup()
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.core.management import call_command  # noqa: E402
import geopandas as gpd  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402
from shapely.geometry import box  # noqa: E402


def squares(n):
    side, d = int(n ** 0.5) + 1, 0.001
    return [box(77.5 + (i % side) * d * 1.5, 12.9 + (i // side) * d * 1.5,
                77.5 + (i % side) * d * 1.5 + d, 12.9 + (i // side) * d * 1.5 + d) for i in range(n)]


def shapefile_zip(n) -> bytes:
    gdf = gpd.GeoDataFrame({"name": [f"p{i}" for i in range(n)]}, geometry=squares(n), crs=4326)
    with tempfile.TemporaryDirectory() as tmp:
        gdf.to_file(Path(tmp) / "bench.shp", engine="pyogrio")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in Path(tmp).iterdir():
                zf.write(f, f.name)
        return buf.getvalue()


def kml(n) -> bytes:
    pms = "".join(
        f"<Placemark><name>p{i}</name><Polygon><outerBoundaryIs><LinearRing><coordinates>"
        + " ".join(f"{x},{y}" for x, y in g.exterior.coords)
        + "</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"
        for i, g in enumerate(squares(n)))
    return f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>{pms}</Document></kml>'.encode()


def main():
    call_command("migrate", verbosity=0)
    client = APIClient()
    post = lambda name, data: client.post("/api/files/", {"file": SimpleUploadedFile(name, data)}, format="multipart")  # noqa: E731
    post("warm.kml", kml(5))  # first call just warms up the imports
    stages = ["parsing", "validating_geometry", "selecting_crs", "transforming", "measuring", "storing"]
    print(f"{'format':9} {'features':>8} {'POST ms':>9} " + " ".join(f"{s[:10]:>10}" for s in stages) + f" {'GET ms':>8} {'peak MB':>8}")
    for n in (10, 100, 1_000, 10_000):
        for fmt, name, make in (("shapefile", "bench.zip", shapefile_zip), ("kml", "bench.kml", kml)):
            data = make(n)
            tracemalloc.start()
            t0 = time.perf_counter()
            body = post(name, data).json()
            wall = (time.perf_counter() - t0) * 1000
            peak = tracemalloc.get_traced_memory()[1] / 1e6
            tracemalloc.stop()
            assert body["successful_count"] == n, body.get("error_message")
            t1 = time.perf_counter()
            assert len(client.get(f"/api/files/{body['id']}/measurements/").json()["features"]) == n
            get_ms = (time.perf_counter() - t1) * 1000
            by = {s["stage"]: s["duration_ms"] for s in body["stages"]}
            print(f"{fmt:9} {n:>8,} {wall:>9,.0f} " + " ".join(f"{by.get(s, 0):>10,.1f}" for s in stages)
                  + f" {get_ms:>8,.0f} {peak:>8.1f}")


if __name__ == "__main__":
    main()
