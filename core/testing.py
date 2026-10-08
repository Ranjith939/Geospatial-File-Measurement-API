"""Helpers shared by the test suites."""
import io
import zipfile
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[1] / "sample-data"


def make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def kml(body: str) -> bytes:
    return (f'<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>{body}'
            "</Document></kml>").encode()
