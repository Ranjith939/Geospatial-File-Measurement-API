"""Generate the deterministic sample datasets.

    .venv/Scripts/python sample-data/generate_samples.py

Shapes are authored in UTM zone 43N (EPSG:32643, around Bengaluru) where their true size is
known exactly, then written either in that projected CRS or converted to WGS84. Expected
values are listed in sample-data/README.md and asserted in backend/tests.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box

OUT = Path(__file__).resolve().parent
TO_WGS84 = Transformer.from_crs(32643, 4326, always_xy=True)
E0, N0 = 777_000.0, 1_432_000.0  # ~ 77.59 E, 12.95 N


def ll(x, y):
    return TO_WGS84.transform(x, y)


def kml_coords(pts):
    return " ".join(f"{lon:.9f},{lat:.9f},0" for lon, lat in (ll(x, y) for x, y in pts))


def placemark(name, geom_xml, pid=None, data=None):
    ext = "".join(f'<Data name="{k}"><value>{v}</value></Data>' for k, v in (data or {}).items())
    ext = f"<ExtendedData>{ext}</ExtendedData>" if ext else ""
    attr = f' id="{pid}"' if pid else ""
    return f"<Placemark{attr}><name>{name}</name>{ext}{geom_xml}</Placemark>"


def poly_xml(ring, holes=()):
    inner = "".join(f"<innerBoundaryIs><LinearRing><coordinates>{kml_coords(h)}</coordinates></LinearRing></innerBoundaryIs>" for h in holes)
    return f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{kml_coords(ring)}</coordinates></LinearRing></outerBoundaryIs>{inner}</Polygon>"


def line_xml(pts):
    return f"<LineString><coordinates>{kml_coords(pts)}</coordinates></LineString>"


def point_xml(x, y):
    return f"<Point><coordinates>{kml_coords([(x, y)])}</coordinates></Point>"


def kml_doc(name, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">'
            f"<Document><name>{name}</name>{body}</Document></kml>\n")


def square(x, y, side):
    return [(x, y), (x + side, y), (x + side, y + side), (x, y + side), (x, y)]


def write_kmls():
    # 1 km x 1 km = 1,000,000 m2 = 100 ha; second parcel 400 x 250 m with a 100 x 100 m hole = 90,000 m2.
    body = placemark("Parcel A", poly_xml(square(E0, N0, 1000)), "parcel-a", {"owner": "Survey Dept", "zone": "R1"})
    body += placemark("Parcel B", poly_xml(
        [(E0 + 1500, N0), (E0 + 1900, N0), (E0 + 1900, N0 + 250), (E0 + 1500, N0 + 250), (E0 + 1500, N0)],
        [square(E0 + 1600, N0 + 50, 100)]), "parcel-b", {"owner": "Municipal", "zone": "C2"})
    (OUT / "polygon.kml").write_text(kml_doc("Polygons", body), encoding="utf-8")

    # 600 m + 800 m L-shaped route = 1,400 m
    body = placemark("Service Road", line_xml([(E0, N0), (E0 + 600, N0), (E0 + 600, N0 + 800)]), "road-1",
                     {"surface": "asphalt", "lanes": 2})
    (OUT / "line.kml").write_text(kml_doc("Lines", body), encoding="utf-8")

    body = placemark("Survey Marker", point_xml(E0 + 10, N0 + 10), "bm-1", {"type": "benchmark"})
    (OUT / "point.kml").write_text(kml_doc("Points", body), encoding="utf-8")

    # Mixed: 3 good, 1 point, 3 bad (bow-tie, broken coordinates, unsupported collection).
    good = (placemark("Field 1", poly_xml(square(E0, N0, 200)), "f1", {"crop": "ragi"})
            + placemark("Field 2", poly_xml(square(E0 + 300, N0, 300)), "f2", {"crop": "maize"})
            + placemark("Canal", line_xml([(E0, N0 - 50), (E0 + 1000, N0 - 50)]), "canal", {"kind": "irrigation"})
            + placemark("Well", point_xml(E0 + 100, N0 + 100), "well"))
    bad = (placemark("Bow-tie", poly_xml([(E0, N0 + 400), (E0 + 200, N0 + 600), (E0 + 200, N0 + 400),
                                          (E0, N0 + 600), (E0, N0 + 400)]), "bowtie")
           + '<Placemark id="broken"><name>Broken coords</name><Polygon><outerBoundaryIs><LinearRing>'
             "<coordinates>77.6,12.9,0 not-a-number 77.7</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"
           + '<Placemark id="combo"><name>Point + Line</name><MultiGeometry>' + point_xml(E0, N0)
           + line_xml([(E0, N0), (E0 + 10, N0)]) + "</MultiGeometry></Placemark>")
    body = f"<Folder><name>Valid</name>{good}</Folder><Folder><name>Problems</name>{bad}</Folder>"
    (OUT / "mixed_geometry.kml").write_text(kml_doc("Mixed geometry", body), encoding="utf-8")


def zip_shapefile(gdf, name, zip_name, drop=(), flat=False):
    with tempfile.TemporaryDirectory() as tmp:
        gdf.to_file(Path(tmp) / f"{name}.shp", engine="pyogrio")
        with zipfile.ZipFile(OUT / zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(Path(tmp).iterdir()):
                if f.suffix.lower() not in drop:
                    zf.write(f, f.name if flat else f"{name}/{f.name}")


def write_shapefiles():
    # Projected source: measured directly in EPSG:32643, so areas are exact.
    parcels = gpd.GeoDataFrame(
        {"parcel_id": ["P-001", "P-002", "P-003"], "owner": ["A. Rao", "B. Iyer", "C. Khan"],
         "land_use": ["agri", "agri", "residential"]},
        geometry=[box(E0, N0, E0 + 500, N0 + 400), box(E0 + 600, N0, E0 + 800, N0 + 500),
                  Polygon(square(E0, N0 + 500, 300))],
        crs=32643)
    zip_shapefile(parcels, "parcels", "valid_shapefile.zip")
    zip_shapefile(parcels, "parcels", "invalid_shapefile.zip", drop={".shx"})
    zip_shapefile(parcels, "parcels", "missing_crs.zip", drop={".prj"})
    (OUT / "corrupt.zip").write_bytes(b"PK\x03\x04" + b"\x00garbage" * 64)

    # Demo dataset in WGS84: a 14 x 14 grid of 198 cells; cells 83 and 141 hold self-intersecting
    # "bow-tie" parcels, so 196 succeed and 2 fail in the middle of the file.
    rows, geoms = [], []
    for i in range(198):
        r, c = divmod(i, 14)
        x, y = E0 + c * 400, N0 + r * 400
        if i + 1 in (83, 141):
            geoms.append(Polygon([ll(*p) for p in [(x, y), (x + 300, y + 300), (x + 300, y), (x, y + 300), (x, y)]]))
            rows.append({"parcel_no": i + 1, "village": "Disputed", "survey_m2": None})
            continue
        side = 150 + (i * 37) % 200  # deterministic 150..349 m
        geoms.append(Polygon([ll(px, py) for px, py in square(x, y, side)]))
        rows.append({"parcel_no": i + 1, "village": ["Hebbal", "Yelahanka", "Jakkur", "Kogilu"][i % 4],
                     "survey_m2": float(side * side)})
    zip_shapefile(gpd.GeoDataFrame(rows, geometry=geoms, crs=4326), "land_parcels", "land_parcels.zip")

    # The landing story's subject: one irregular surveyed parcel, WGS84 with .prj. Its area is
    # whatever the shoelace formula gives in UTM 43N; SURVEY_M2 records that for the tests.
    ring = [(E0 + 120, N0 + 40), (E0 + 395, N0), (E0 + 520, N0 + 180), (E0 + 455, N0 + 330),
            (E0 + 240, N0 + 395), (E0 + 30, N0 + 290), (E0, N0 + 140), (E0 + 120, N0 + 40)]
    survey = Polygon(ring)
    gpd.GeoDataFrame({"parcel_id": ["SV-12/4"], "owner": ["Gram Panchayat"], "land_use": ["orchard"],
                      "survey_m2": [round(survey.area, 2)]},
                     geometry=[Polygon([ll(*p) for p in ring])], crs=4326).pipe(
        lambda g: zip_shapefile(g, "survey", "survey.zip", flat=True))

    # Lines + points shapefile in WGS84.
    roads = gpd.GeoDataFrame({"name": ["Ring Rd", "Link Rd"], "lanes": [4, 2]},
                             geometry=[LineString([ll(E0, N0), ll(E0 + 2000, N0)]),
                                       LineString([ll(E0, N0), ll(E0, N0 + 500), ll(E0 + 300, N0 + 900)])],
                             crs=4326)
    zip_shapefile(roads, "roads", "roads_wgs84.zip")


if __name__ == "__main__":
    write_kmls()
    write_shapefiles()
    for f in sorted(OUT.iterdir()):
        if f.suffix in (".kml", ".zip"):
            print(f"{f.name:28s} {f.stat().st_size:>8,d} B")
    shutil.rmtree(OUT / "__pycache__", ignore_errors=True)
