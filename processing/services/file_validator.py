"""Checks the upload's name, size and actual content. I never trust the extension by itself here."""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from core.exceptions import ValidationFailed

SUPPORTED_EXTENSIONS = {".kml": "KML", ".zip": "SHAPEFILE"}
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(name: str | None) -> str:
    """Keeps just the base name with safe characters. We never use this as a storage path."""
    base = Path((name or "").replace("\\", "/")).name
    base = _UNSAFE_CHARS.sub("_", base).strip(" .")
    return base[:200] or "upload"


def detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationFailed(
            "UNSUPPORTED_FILE_TYPE",
            f"Files of type '{ext or 'none'}' are not supported.",
            {"supported": sorted(SUPPORTED_EXTENSIONS)},
            status_code=415,
        )
    return SUPPORTED_EXTENSIONS[ext]


def validate_kml(path: Path) -> None:
    head = path.read_bytes()[:4096].lower()
    # KML never needs entity declarations, and they're how XML bombs and XXE attacks get in, so I reject them.
    if b"<!doctype" in head or b"<!entity" in head:
        raise ValidationFailed("INVALID_KML", "KML files with DOCTYPE or ENTITY declarations are not accepted.")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValidationFailed("INVALID_KML", "The file is not well-formed XML.", {"reason": str(exc)}) from None
    if root.tag.rsplit("}", 1)[-1] != "kml":
        raise ValidationFailed("INVALID_KML", "The XML document is not KML (root element must be <kml>).")


def validate_zip(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        raise ValidationFailed("CORRUPT_ARCHIVE", "The file is not a valid ZIP archive.")
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
    except (zipfile.BadZipFile, OSError, NotImplementedError) as exc:
        raise ValidationFailed("CORRUPT_ARCHIVE", "The ZIP archive could not be read.", {"reason": str(exc)}) from None
    if bad is not None:
        raise ValidationFailed("CORRUPT_ARCHIVE", "The ZIP archive is corrupt.", {"member": bad})


def validate_content(path: Path, file_type: str) -> None:
    if path.stat().st_size == 0:
        raise ValidationFailed("EMPTY_FILE", "The uploaded file is empty.", status_code=400)
    (validate_kml if file_type == "KML" else validate_zip)(path)
